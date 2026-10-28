"""CP-1C Stage 2 connection, fast tests (docs/CP1C-OWNER-LEASE.md Public API, D2, D3, D7, D12).

Everything here runs over hand-built `Module` objects whose facts come from the frozen oracle
(`cases/cp1c-owner`; the CP-1 T4.10 facts are the manifest's recorded probe) or over a real store
whose CP-0 and CP-1 heads are settled from those modules (no CP-1 promotion). The closed runs are
`tests/test_owner_cp1c.py` (deferred to Stage 5). Fixtures vary the CP-1 values and statuses, the
as-of date, the bound statuses and staleness, so a constant equal to the oracle cannot pass.
"""

import copy
import dataclasses
import datetime
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal, cast

import cp1c_runs as runs
import pytest
import test_method_cp1c as stage1
from defect_classes import (
    BLANK_VALUES,
    MODEL_TEXT_HOSTILE,
    assert_hostile_refused,
    free_text_paths,
    model_text_failures,
    path_matches,
    with_text,
)

from deploy_vii import registry
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import (
    Citation,
    Claim,
    Fact,
    Input,
    InputStatus,
    Module,
    ModuleView,
    ReportTable,
    Run,
    View,
    validate_tables,
)
from deploy_vii.execution import (
    MAX_ISSUE_CHARS,
    MAX_ISSUES,
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    candidate_issues,
    settle,
    text_sha256,
)
from deploy_vii.live.tools import Seen, cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import (
    _RELATIVE_VALUE,
    _spec_of,
    _unit_class,
    build,
    fact_spelling,
    pathways,
)
from deploy_workflow import host
from deploy_workflow import owner_workflow as owner
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.owners import cp1c
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]
MODULE = "CP-1C"
STEP = "peer_benchmark"
CASES = stage1.CASES
SYNTHETIC = "Synthetic case; not real issuer qualification"


def _payload(case: str = "positive") -> dict[str, Any]:
    return copy.deepcopy(stage1.submissions()[case][STEP])


def _issues(case: str, payload: dict[str, Any], pack: str | None = None) -> tuple[str, ...]:
    return cp1c.calculation_issues(stage1.inputs(case, pack=pack, payload=payload))


# --- backlog (stage2-backlog.md "Every module"; 0d-c audit f-string sites; protocol section 6) ---

LONG = "Fenwick " + "Z" * 5000


def test_caller_quoting_issue_lines_are_clipped() -> None:
    """The f-string sites (0d-c audit: unknown peer, evidence, limitation) quote the payload's peer
    name through `clipped`: each line is cut to `MAX_ISSUE_CHARS` before it is built whole."""
    payload = _payload()
    payload["assessments"][0].update(
        peer=LONG, comparability="Partly comparable", limitation=None, evidence=[]
    )
    issues = _issues("positive", payload)
    for prefix in (
        "Unknown peer: Fenwick ZZ",
        "Evidence required for a comparability assessment: Fenwick ZZ",
        "Limitation required for Partly comparable: Fenwick ZZ",
    ):
        (line,) = [i for i in issues if i.startswith(prefix)]
        assert len(line) == MAX_ISSUE_CHARS and line.endswith("…"), prefix
    assert "Assess each sheet peer exactly once: Alder Ridge Holdings" in issues


def test_assessment_without_a_peer_source_line_is_clipped() -> None:
    payload = _payload("no_peers")
    payload["assessments"] = [dict(_payload()["assessments"][0], peer=LONG)]
    payload["assessments"][0]["evidence"] = []
    issues = _issues("no_peers", payload)
    line = next(i for i in issues if i.startswith("Assessment given without a peer source"))
    assert len(line) == MAX_ISSUE_CHARS and line.endswith("…")


def test_prose_issue_line_quoting_the_payload_is_clipped() -> None:
    """`prose.issues` quotes a bare figure whole (a reference is capped at 160 characters by the
    product, a word is not), so the module clips each prose line it journals."""
    payload = _payload()
    payload["overall"]["rationale"] = "The peer set has " + "7" * 3000 + " members."
    (line,) = _issues("positive", payload)
    assert line.startswith("Bare figure: 777") and len(line) == MAX_ISSUE_CHARS


def _many_unknown(count: int) -> dict[str, Any]:
    payload = _payload()
    template = payload["assessments"][0]
    payload["assessments"] = [dict(template, peer=f"Unknown peer {n:02d}") for n in range(count)]
    return payload


@pytest.mark.parametrize("count", [3, 30])
def test_the_issue_list_is_bounded_with_a_count_of_the_rest(count: int) -> None:
    """Five sheet peers left unassessed plus `count` unknown peers: at most `MAX_ISSUES` lines,
    the last counting the lines left out (`execution.listed_issues`)."""
    issues = _issues("positive", _many_unknown(count))
    total = count + 5
    if total <= MAX_ISSUES:
        assert len(issues) == total
    else:
        assert len(issues) == MAX_ISSUES
        assert issues[-1] == f"{total - MAX_ISSUES + 1} further issues not listed"
    assert issues[0] == "Unknown peer: Unknown peer 00"


def test_the_raised_join_of_a_refused_payload_is_bounded() -> None:
    with pytest.raises(ValueError) as caught:
        cp1c.compute(stage1.inputs("positive", payload=_many_unknown(200)))
    assert len(str(caught.value)) <= MAX_ISSUES * (MAX_ISSUE_CHARS + 2)
    assert str(caught.value).endswith("further issues not listed")


QUOTE_BLANKS = [v for v in BLANK_VALUES if v]  # "" is refused by the schema (Text)


@pytest.mark.parametrize("blank", QUOTE_BLANKS, ids=repr)
@pytest.mark.parametrize("where", ["assessment", "overall"])
def test_blank_citation_quote_gets_the_empty_text_frame_before_the_page_check(
    where: str, blank: str
) -> None:
    """Round 13 addendum 3 (backlog "Every module"): a quote that `is_blank` is refused with
    `<path>: empty text` and never reaches the page-occurrence check. Inventory: before this,
    CP-1C refused it only as a quote/locator mismatch of the empty reading (fail closed, so the
    Medium defect, a blank quote accepted, was absent)."""
    payload = _payload()
    if where == "assessment":
        payload["assessments"][2]["evidence"][0]["quote"] = blank
        path = "assessments[2].evidence[0].quote"
    else:
        payload["overall"]["evidence"] = [dict(payload["assessments"][0]["evidence"][0])]
        payload["overall"]["evidence"][0]["quote"] = blank
        path = "overall.evidence[0].quote"
    assert _issues("positive", payload) == (f"{path}: empty text",)


def test_a_non_blank_quote_still_gets_the_page_check() -> None:
    payload = _payload()
    payload["assessments"][2]["evidence"][0]["quote"] = "A sentence that is not on the page."
    (line,) = _issues("positive", payload)
    assert line.startswith("Quote/locator mismatch: quote not found under peers page:2 (")


@pytest.mark.parametrize(
    "amount",
    ["1,250.0", "200,0", "200.00", "(200.0)", "200.0m", "US$200.0", "2 00.0"],
)
def test_peer_table_guard_limits_noted_in_the_method(amount: str) -> None:
    """Item 8 comma costs and the table rule's other edges (methods/cp1c.md "Peer table guard
    limits"): a grouped amount, a decimal comma, two decimal places, a parenthesised negative, a
    unit or currency on the amount, or a split figure is no amount of the rule, so the whole table
    is `Peer table not found`. Fails closed; no reading rule is added (Source quotes)."""
    line = stage1.ALDER.replace("200.0", amount)
    case = stage1._with_sources("positive", stage1._edited("positive", 1, stage1.ALDER, line))
    assert cp1c.calculation_issues(case) == ("Peer table not found",)


def test_method_note_exists_and_names_each_stage_2_rule() -> None:
    text = (ROOT / "src" / "deploy_vii" / "methods" / "cp1c.md").read_text()
    assert not (ROOT / "docs" / "methods-drafts" / "cp1c.md").exists()
    for needle in (
        "## Stage 2 notes",
        "Source quotes",
        "Peer table guard limits",
        "`1,250.0`",
        "lineage",
        "one `Citation` per (source, page)",
        ": empty text",
        "`RunText`",
        "Synthetic case; not real issuer qualification",
        "`cp1c_reader(store, head)`",
        "listed_issues",
    ):
        assert needle in text, needle


# --- shared fixtures for the connection ----------------------------------------------------------

AS_OF = datetime.date(2026, 1, 10)
FIN_SHA = "82d684ccaa230ca1ff5ada477b02b510c193b0deabf7cd749e420508f93c0429"
CP1_CITE = Citation(
    source_id="financial",
    source_sha256=FIN_SHA,
    locator="page:1",
    quote="Currency: USD; amounts in millions.",
)
LTM = "LTM Q4 25: 2025-01-01 to 2025-12-31"


def _run(case: str, as_of: datetime.date | None = None) -> Run:
    run_case = case if case in stage1.manifest()["cases"] else "positive"
    document = dict(stage1.manifest()["cases"][run_case]["run"])
    if as_of is not None:
        document["as_of"] = as_of.isoformat()
    return Run.model_validate_json(json.dumps(document))


def _pack(
    case: str, *, base: str | None = None, as_of: datetime.date | None = None
) -> PreparedPack:
    """The run of `base` (default `case`) over the host-scoped sources of pack `case`."""
    return PreparedPack(run=_run(base or case, as_of), sources=stage1.sources(case))


def _metrics(
    scale: Decimal = Decimal(1), cited: bool = False, not_known: bool = False
) -> dict[str, Fact]:
    """The four CP-1 T4.10 LTM facts of the manifest probe, amounts times `scale`; `not_known`
    takes the Stage 1 B1 fixture (margin missing, coverage not applicable)."""
    base = stage1._cp1_not_known() if not_known else stage1.cp1_metrics()
    out: dict[str, Fact] = {}
    for key, fact in base.items():
        update: dict[str, Any] = {"citations": (CP1_CITE,) if cited else ()}
        if fact.amount is not None:
            update["amount"] = cp1c.CTX.multiply(fact.amount, scale)
        out[key] = fact.model_copy(update=update)
    return out


def _cp1_module(
    metrics: dict[str, Fact] | None = None, *, as_of: datetime.date = AS_OF, decoys: bool = True
) -> Module:
    """A CP-1 head holding the four facts, each with an FY25 decoy (same label, other period) and
    a T4.9 decoy (same label and period, other table); only the T4.10 LTM facts are selected."""
    chosen = _metrics() if metrics is None else metrics
    facts: list[Fact] = []
    for key, fact in chosen.items():
        facts.append(fact)
        if decoys:
            facts.append(fact.model_copy(update={"fact_id": f"fy25-{key}", "period": "FY25: 2025"}))
            facts.append(fact.model_copy(update={"fact_id": f"t49-{key}", "table_id": "T4.9"}))
    return Module(
        run_id="cp1c-owner-positive",
        issuer_id="northbridge-synthetic",
        as_of=as_of,
        module_id="CP-1",
        status="restricted",
        facts=tuple(facts),
        limitations=("CP-1 note",),
    )


def _cp0_module(as_of: datetime.date = AS_OF) -> Module:
    return Module(
        run_id="cp1c-owner-positive",
        issuer_id="northbridge-synthetic",
        as_of=as_of,
        module_id="CP-0",
        status="restricted",
        limitations=("CP-0 note",),
    )


def _upstream(
    cp1: Module | None = None,
    *,
    cp1_status: InputStatus = "restricted",
    inherited: tuple[str, ...] = (),
) -> "cp1c.Upstream":
    cp0, head = _cp0_module(), _cp1_module() if cp1 is None else cp1
    bound = (
        Input(input_id="CP-0", sha256=cp0.content_hash(), status="restricted"),
        Input(input_id="CP-1", sha256=head.content_hash(), status=cp1_status),
    )
    return cp1c.Upstream(bound=bound, current=bound, cp0=cp0, cp1=head, inherited=inherited)


def _submission(case: str = "positive", payload: Any = None) -> cp1c.PeerBenchmarkSubmission:
    body = _payload(case) if payload is None else payload
    return cp1c.PeerBenchmarkSubmission.model_validate_json(json.dumps(body))


def _report(
    case: str, upstream: "cp1c.Upstream | None" = None, pack: PreparedPack | None = None
) -> "cp1c.PeerBenchmarkReport":
    return cp1c.peer_benchmark(
        pack=_pack(case) if pack is None else pack,
        submission=_submission(case),
        upstream=_upstream() if upstream is None else upstream,
    )


def _module(case: str, upstream: "cp1c.Upstream | None" = None) -> Module:
    up = _upstream() if upstream is None else upstream
    return cp1c.cp1c_module(_report(case, up), inputs=up.bound, attempt=0)


# --- the plug-in parts (protocol section 2) -------------------------------------------------------


def test_core_attributes_match_the_lease() -> None:
    assert (cp1c.MODULE_ID, cp1c.STEP_ID, cp1c.STEP_IDS) == (MODULE, STEP, (STEP,))
    assert cp1c.QUALIFICATION == Qualification(implementation="implemented")
    assert dict(cp1c.SCHEMAS) == {STEP: cp1c.PeerBenchmarkSubmission}
    assert cp1c.SUBMISSION_INPUT == "peer-benchmark-submission"
    for name in (
        "RULES",
        "parse_peer_source",
        "peer_metrics",
        "median",
        "position",
        "outlier",
        "cp1c_upstream",
        "validate_peer_benchmark",
        "peer_benchmark",
        "context_block",
        "cp1c_module",
        "submit",
        "view",
        "probe",
        "cp1c_reader",
        "ENTRY_VALIDATOR",
    ):
        assert callable(getattr(cp1c, name)), name
    assert not hasattr(cp1c, "precheck")  # lease: no precheck, every rule is journaled


@pytest.mark.parametrize("case", CASES)
def test_schemas_round_trip_and_give_the_tail_digest(case: str) -> None:
    schema = cp1c.SCHEMAS[STEP]
    parsed = schema.model_validate_json(json.dumps(_payload(case)))
    assert schema.model_validate_json(parsed.model_dump_json()) == parsed
    up = _upstream()
    module = cp1c.cp1c_module(_report(case, up), inputs=up.bound, attempt=0)
    tail = module.inputs[len(up.bound) :]
    assert [(i.input_id, i.sha256) for i in tail] == [
        ("peer-benchmark-submission", parsed.content_hash())
    ]


def test_shared_hostile_text_set_over_the_schemas() -> None:
    """Rulings stage 2 Q5: the schema refuses the hostile set only with `ValueError`."""
    for schema in cp1c.SCHEMAS.values():
        assert_hostile_refused(schema)


def test_rules_reproduce_the_tool_refusal_and_only_that() -> None:
    payload = json.dumps(_payload())
    refusal = next(t for t in stage1.expected()["tool_refusals"] if t["id"] == "t01")
    want = tuple(refusal["expected_issues"])
    assert cp1c.RULES(payload, Seen()) == want
    assert cp1c.RULES(payload, Seen(read=frozenset({("peers", "page:2")}))) == ()
    assert cp1c.RULES(payload, Seen(read=frozenset({("peers", "page:1")}))) == want
    assert cp1c.RULES("[1,", Seen()) == ()  # never raises on malformed model text
    no_peers = json.dumps(_payload("no_peers"))
    assert cp1c.RULES(no_peers, Seen()) == ()  # no citation, no absence rule (lease Q13)


def test_payload_text_is_parsed_through_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protocol section 6: the schema sees only the bounded document's exact re-serialisation;
    text `json_object` refuses is the admitted shape issue and never reaches the schema."""
    seen: list[str] = []
    original = cp1c.PeerBenchmarkSubmission.model_validate_json

    def spy(text: str | bytes, **kwargs: Any) -> cp1c.PeerBenchmarkSubmission:
        seen.append(text if isinstance(text, str) else text.decode())
        return original(text, **kwargs)

    monkeypatch.setattr(cp1c.PeerBenchmarkSubmission, "model_validate_json", spy)
    spaced = json.dumps(_payload(), indent=2)
    submission, shape = cp1c._parsed(spaced)
    assert submission == _submission() and shape == ()
    assert seen and spaced not in seen
    seen.clear()
    for hostile in ('{"a": "\\ud800"}', "[" * 5000 + "]" * 5000, '{"x": NaN}', "[1,", '"text"'):
        assert cp1c._parsed(hostile) == (None, (cp1c.BAD_PAYLOAD,))
    assert seen == []
    assert cp1c.BAD_PAYLOAD == "(root): not a JSON object within the payload bounds"
    extra = json.dumps({**_payload(), "x" * 5000: 1})
    none, issues = cp1c._parsed(extra)
    assert none is None and issues and all(len(i) <= MAX_ISSUE_CHARS for i in issues)


# --- the store adapter (one adapter for submit, probe and view) -------------------------------


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("status", ["restricted", "accepted"])
def test_adapter_returns_the_stage_1_input_object(case: str, status: InputStatus) -> None:
    mine = cp1c._inputs(_pack(case), _submission(case), _upstream(cp1_status=status))
    assert mine == stage1.inputs(case)


def test_adapter_keeps_only_the_scoped_sources() -> None:
    """A pack source outside the fixed H1 scope (here `business`) never reaches the core."""
    pack = _pack("positive")
    extra = pack.sources[0].model_copy(update={"source_id": "business", "name": "Business note"})
    wide = PreparedPack(run=pack.run, sources=(*pack.sources, extra))
    mine = cp1c._inputs(wide, _submission(), _upstream())
    assert [s.source_id for s in mine.sources] == ["identity", "financial", "peers"]
    assert tuple(sorted(cp1c.SCOPE)) == ("financial", "identity", "peers")


@pytest.mark.parametrize("scale", [Decimal(1), Decimal(2), Decimal("0.5")])
def test_adapter_reads_the_cp1_head_not_a_constant(scale: Decimal) -> None:
    metrics = _metrics(scale)
    mine = cp1c._inputs(_pack("positive"), _submission(), _upstream(_cp1_module(metrics)))
    assert dict(mine.cp1_metrics) == metrics


def test_adapter_carries_an_unsettled_cp1_fact_through_the_b1_path() -> None:
    metrics = _metrics(not_known=True)
    up = _upstream(_cp1_module(metrics))
    mine = cp1c._inputs(_pack("positive"), _submission(), up)
    assert mine.cp1_metrics["adjusted_ebitda_margin"].status == "missing"
    payload = stage1._plain("positive")
    report = cp1c.peer_benchmark(
        pack=_pack("positive"), submission=_submission(payload=payload), upstream=up
    )
    facts = {f.fact_id: f for f in report.facts}
    assert facts["T1C.3.issuer.adjusted_ebitda_margin"].status == "missing"
    assert facts["T1C.3.issuer.interest_coverage_adjusted"].status == "not_applicable"


def test_adapter_refuses_a_cp1_head_without_exactly_one_selected_fact() -> None:
    head = _cp1_module()
    gone = head.model_copy(
        update={"facts": tuple(f for f in head.facts if f.fact_id != "T4.10.ltm.ffo_to_debt")}
    )
    twin = head.facts[0].model_copy(update={"fact_id": "dup-1"})
    double = head.model_copy(update={"facts": (*head.facts, twin)})
    for cp1, count in ((gone, 0), (double, 2)):
        issues = cp1c.validate_peer_benchmark(
            pack=_pack("positive"), submission=_submission(), upstream=_upstream(cp1)
        )
        assert len(issues) == 1 and issues[0].startswith("CP-1 facts unavailable: CP-1 T4.10 ")
        assert f": {count} facts, expected exactly one" in issues[0]


def test_a_known_cp1_fact_breaking_the_stage_1_rules_is_an_issue_not_a_raise() -> None:
    metrics = _metrics()
    metrics["total_leverage_adjusted"] = metrics["total_leverage_adjusted"].model_copy(
        update={"unit": "PERCENT"}
    )
    issues = cp1c.validate_peer_benchmark(
        pack=_pack("positive"), submission=_submission(), upstream=_upstream(_cp1_module(metrics))
    )
    assert issues == ("CP-1 facts unavailable: CP-1 fact unavailable for total_leverage_adjusted",)


# --- the validator and the refusals ---------------------------------------------------------------


def _matches(issue: str, want: str) -> bool:
    return issue.startswith(want) if want.endswith("(") else issue == want


@pytest.mark.parametrize("refusal", stage1.expected()["refusals"], ids=lambda r: r["id"])
def test_validator_reproduces_the_oracle_refusals(refusal: Any) -> None:
    literal = next(r for r in stage1.submissions()["refusals"] if r["id"] == refusal["id"])
    issues = cp1c.validate_peer_benchmark(
        pack=_pack(literal["pack"], base=refusal["base_case"]),
        submission=_submission(payload=literal["payload"]),
        upstream=_upstream(),
    )
    want = refusal["expected_issues"]
    assert len(issues) == len(want), issues
    assert all(_matches(got, w) for got, w in zip(issues, want, strict=True)), issues


def test_validator_reports_stale_and_swapped_inputs_alone() -> None:
    pack, good, up = _pack("positive"), _submission(), _upstream()
    stale = dataclasses.replace(up, current=(up.bound[0],))
    found = cp1c.validate_peer_benchmark(pack=pack, submission=good, upstream=stale)
    assert found == (
        "Stale input CP-1: bound restricted " + up.bound[1].sha256[:12] + ", current absent",
    )
    refused = dataclasses.replace(up, current="CP-0 has not authorized " + "x" * 2000)
    (line,) = cp1c.validate_peer_benchmark(pack=pack, submission=good, upstream=refused)
    assert line.startswith("Stale inputs: CP-0 has not authorized") and len(line) == MAX_ISSUE_CHARS
    swapped = dataclasses.replace(up, cp1=_cp1_module(_metrics(Decimal(2))))
    assert cp1c.validate_peer_benchmark(pack=pack, submission=good, upstream=swapped) == (
        "Upstream CP-1: the supplied module is not the bound input",
    )


def test_rationale_is_checked_with_the_type_the_claim_builds() -> None:
    """Rulings stage 2 round 3 item 2: a rationale becomes `Claim.text`, so it is checked as
    `RunText` (the type's own message, never the input) before anything is built from it."""
    payload = _payload()
    payload["assessments"][1]["rationale"] = "The peer of {broken is aligned."
    submission = _submission(payload=payload)
    direct = cp1c._model_text_issues(submission)
    assert direct == [
        "assessments[1].rationale: Value error, Malformed run text: unbalanced or empty reference"
    ]
    issues = cp1c.validate_peer_benchmark(
        pack=_pack("positive"), submission=submission, upstream=_upstream()
    )
    assert issues and all("{broken" not in i for i in issues)
    assert cp1c._model_text_issues(_submission()) == []


# Round 5 item 10 M1: the paths whose value is stored as plain text and never built as run text,
# with their sinks. Every other free-text path must journal an issue for hostile model text.
CP1C_VERBATIM: frozenset[tuple[str | int, ...]] = frozenset(
    {
        ("assessments", "*", "limitation"),  # Claim.limitation; own limitation line
        ("overall", "limitation"),  # Claim.limitation of T1C.1.assessment
        ("gaps", "*", "gap"),  # T1C.7 Fact.text; own limitation "Gap (<severity>): <gap>"
        ("gaps", "*", "why_it_matters"),  # T1C.7 Fact.text
        ("gaps", "*", "affected_analysis"),  # T1C.7 Fact.text
        ("gaps", "*", "action"),  # T1C.7 Fact.text
    }
)


def test_model_text_is_refused_or_stored_verbatim() -> None:
    """Round 3 item 2 and round 5 item 10 at the validator (the run-level form, with the wedge
    check, is the next test): every hostile value on every free-text path is an issue, except
    on the `CP1C_VERBATIM` paths, where it composes and is stored as plain text."""
    payload = _payload()
    paths = free_text_paths(payload, cp1c.PeerBenchmarkSubmission)
    assert all(any(path_matches(p, path) for path in paths) for p in CP1C_VERBATIM)
    for path in paths:
        for value in MODEL_TEXT_HOSTILE:
            body = with_text(payload, path, value)
            issues = cp1c.validate_peer_benchmark(
                pack=_pack("positive"), submission=_submission(payload=body), upstream=_upstream()
            )
            if any(path_matches(p, path) for p in CP1C_VERBATIM):
                assert issues == (), (path, value)
                module = cp1c.cp1c_module(
                    cp1c.peer_benchmark(
                        pack=_pack("positive"),
                        submission=_submission(payload=body),
                        upstream=_upstream(),
                    ),
                    inputs=_upstream().bound,
                    attempt=0,
                )
                stored = [*(f.text for f in module.facts), *(c.limitation for c in module.claims)]
                assert value in stored, (path, value)
            else:
                assert issues, (path, value)


# --- the composed report and the module ------------------------------------------------------------


def _cites(citations: Any) -> list[tuple[str, str, str]]:
    return [
        (c["source_id"], c["locator"], c["quote"])
        if isinstance(c, dict)
        else (c.source_id, c.locator, c.quote)
        for c in citations
    ]


def assert_equals_oracle(
    case: str,
    facts: tuple[Fact, ...],
    tables: tuple[ReportTable, ...],
    claims: tuple[Claim, ...],
    cp1: dict[str, Fact],
) -> None:
    """Facts, tables and claims against `expected.json cases.<case>`. `cp1` is the selected CP-1
    T4.10 fact of each metric: a copied cell equals it (amount, unit, value class, calculation id,
    citations), and the CP-1 citations a derived fact carries at run time are set aside before
    the literal comparison (`expected.lineage_rule`)."""
    want = stage1.expected()["cases"][case]
    cp1_cites = {c for fact in cp1.values() for c in fact.citations}
    assert [f.fact_id for f in facts] == [f["fact_id"] for f in want["facts"]]
    for fact, expect in zip(facts, want["facts"], strict=True):
        assert (fact.status, fact.unit, fact.period, fact.text, fact.value_class) == (
            expect["status"],
            expect.get("unit"),
            expect.get("period"),
            expect.get("text"),
            expect.get("value_class"),
        ), fact.fact_id
        assert stage1._exact(fact.amount) == expect.get("amount_exact"), fact.fact_id
        assert fact.limitation == expect.get("limitation"), fact.fact_id
        if expect.get("copied_from_cp1"):
            parts = fact.fact_id.split(".")
            source = cp1[parts[3] if parts[1] == "3" else parts[2]]
            assert fact.model_dump(include=COPIED) == source.model_dump(include=COPIED), (
                fact.fact_id
            )
        else:
            literal = [c for c in fact.citations if c not in cp1_cites]
            assert _cites(literal) == _cites(expect.get("citations", [])), fact.fact_id
            assert fact.calculation_id == expect.get("calculation_id"), fact.fact_id
    assert [t.table_id for t in tables] == [t["table_id"] for t in want["tables"]]
    for table, expect_t in zip(tables, want["tables"], strict=True):
        assert table.title == expect_t["title"]
        assert [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] == [
            (r["row_id"], r["label"], r["fact_ids"]) for r in expect_t["rows"]
        ]
    assert [c.claim_id for c in claims] == [c["claim_id"] for c in want["claims"]]
    for claim, expect_c in zip(claims, want["claims"], strict=True):
        assert (claim.text, claim.limitation) == (expect_c["text"], expect_c["limitation"])
        assert _cites(claim.citations) == _cites(expect_c.get("evidence", []))


COPIED = {"amount", "unit", "value_class", "calculation_id", "citations"}


@pytest.mark.parametrize("case", CASES)
def test_report_facts_tables_claims_and_limitations_equal_the_oracle(case: str) -> None:
    report = _report(case)
    assert_equals_oracle(case, report.facts, report.tables, report.claims, _metrics())
    assert list(report.limitations) == stage1.expected()["cases"][case]["own_limitations"]
    assert report.submission_sha256 == _submission(case).content_hash()
    assert report.pack_sha256 == _pack(case).content_hash()


def test_copied_cells_carry_cp1_citations_and_calculation_id_at_run_time() -> None:
    metrics = _metrics(cited=True)
    report = _report("positive", _upstream(_cp1_module(metrics)))
    facts = {f.fact_id: f for f in report.facts}
    for key, source in metrics.items():
        for fid in (f"T1C.3.issuer.{key}", f"T1C.6.{key}.cp1"):
            copy_ = facts[fid]
            assert (copy_.amount, copy_.calculation_id, copy_.citations) == (
                source.amount,
                source.calculation_id,
                (CP1_CITE,),
            ), fid
    # a fact derived from a copied cell carries CP-1's citation at that cell's place
    position = facts["T1C.4.total_leverage_adjusted.position"]
    assert position.citations[0] == CP1_CITE and len(position.citations) == 5


def test_report_follows_the_cp1_head() -> None:
    """A CP-1 head with leverage 2.5x moves the issuer's copy, difference, position and the
    tie-out (the issuer line still says 50 / 30), so a constant equal to the oracle fails."""
    metrics = _metrics()
    metrics["total_leverage_adjusted"] = metrics["total_leverage_adjusted"].model_copy(
        update={"amount": Decimal("2.5")}
    )
    facts = {f.fact_id: f for f in _report("positive", _upstream(_cp1_module(metrics))).facts}
    assert facts["T1C.3.issuer.total_leverage_adjusted"].amount == Decimal("2.5")
    assert facts["T1C.4.total_leverage_adjusted.difference"].amount == Decimal(0)
    assert facts["T1C.4.total_leverage_adjusted.position"].amount == Decimal(3)
    assert facts["T1C.6.total_leverage_adjusted.result"].text == "Differs"


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("as_of", [AS_OF, datetime.date(2026, 3, 31)])
def test_module_passes_the_candidate_checks_and_settles_the_oracle_limitations(
    case: str, as_of: datetime.date
) -> None:
    """A head built by `settle` over the real candidate: `candidate_issues` (identity, bound
    inputs, citations against the pack, claims against the module's facts) is empty; own
    limitations are the oracle list then the synthetic line (round 3 item 5)."""
    cp1 = _cp1_module(_metrics(cited=True), as_of=as_of)
    up = _upstream(cp1)
    pack = _pack(case, as_of=as_of)
    candidate = cp1c.cp1c_module(_report(case, up, pack), inputs=up.bound, attempt=0)
    payload = candidate.model_dump_json()
    attempt = Attempt(
        ticket_id="t1",
        module_id=MODULE,
        inputs=up.bound,
        number=0,
        payload_sha256=text_sha256(payload),
    )
    snapshot = ExecutionSnapshot(run=pack.run, pack_sha256=pack.content_hash(), attempts=(attempt,))
    assert candidate_issues(snapshot, attempt, candidate, pack=pack) == ()
    finished, head = settle(
        snapshot,
        attempt,
        payload,
        lambda supplied: () if supplied == candidate else ("Candidate differs",),
        pack=pack,
        load=lambda _head: candidate,
    )
    assert finished.issues == ()
    assert head.status == stage1.expected()["cases"][case]["module_status"]
    own = stage1.expected()["cases"][case]["own_limitations"]
    assert list(head.limitations) == [*own, SYNTHETIC]
    assert list(head.limitations) == stage1.expected()["cases"][case]["settled_limitations"]


# --- the exact `read_inputs` view (lease Tool use, D2) ----------------------------------------------

FORBIDDEN_KEYS = {"quote", "citations", "record_json"}


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _strings(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in _strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in _strings(v)]
    return []


@pytest.mark.parametrize("case", CASES)
def test_view_matches_the_lease_key_tree_and_holds_no_quote(case: str) -> None:
    up = _upstream(inherited=("An inherited line",))
    block = cp1c.context_block(pack=_pack(case), upstream=up)
    assert list(block) == ["upstream", "peers", "cp1_facts", "rules", "inherited_limitations"]
    assert block["upstream"] == [
        {"module_id": "CP-0", "status": "restricted"},
        {"module_id": "CP-1", "status": "restricted"},
    ]
    assert block["inherited_limitations"] == ["An inherited line"]
    peers = block["peers"]
    assert isinstance(peers, dict)
    assert list(peers) == ["state", "source_id", "pages", "rows", "issuer_line"]
    rows = peers["rows"]
    assert isinstance(rows, list)
    if case == "no_peers":
        assert peers == {
            "state": "absent",
            "source_id": None,
            "pages": [],
            "rows": [],
            "issuer_line": None,
        }
    else:
        assert (peers["state"], peers["source_id"], peers["pages"]) == (
            "present",
            "peers",
            ["page:1", "page:2"],
        )
        labels = [r["label"] for r in rows]
        assert labels == [r["label"] for r in stage1.expected()["cases"][case]["tables"][0]["rows"]]
        assert all(list(r) == ["row", "label", "period_end", "amounts", "basis"] for r in rows)
        assert peers["issuer_line"]["label"] == "Northbridge Synthetic Group"
    facts = block["cp1_facts"]
    assert isinstance(facts, list)
    assert [f["ref"] for f in facts] == [f"T1C.3.issuer.{m.key}" for m in cp1c.METRICS]
    assert all(list(f) == ["ref", "label", "period", "unit", "shown", "value_class"] for f in facts)
    assert [f["shown"] for f in facts] == ["25.0%", "1.67x", "6.00x", "42.0%"]
    assert [f["unit"] for f in facts] == ["%", "x", "x", "%"]
    rules = block["rules"]
    assert isinstance(rules, dict)
    assert list(rules) == [
        "minimum_included_peers",
        "outlier_fraction",
        "inclusion",
        "position",
        "direction",
    ]
    assert (rules["minimum_included_peers"], rules["outlier_fraction"]) == (3, "0.5")
    assert not FORBIDDEN_KEYS & _keys(block)
    pages = [s.text for src in _pack(case).sources for s in src.spans]
    for text in _strings(block):  # no quote: no string of the view is a long span of a page
        assert not (len(text) > 30 and any(text in page for page in pages)), text


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_view_rows_spell_the_t1c2_cells(case: str) -> None:
    block = cp1c.context_block(pack=_pack(case), upstream=_upstream())
    shown = {f["fact_id"]: f["shown"] for f in stage1.expected()["cases"][case]["facts"]}
    peers = block["peers"]
    assert isinstance(peers, dict)
    for row in [peers["issuer_line"], *peers["rows"]]:
        for key, text in row["amounts"].items():
            want = shown[f"T1C.2.{row['row']}.{key}"]
            assert text == ("Not stated" if want is None else want), (row["row"], key)
    if case == "gap":
        p03 = next(r for r in peers["rows"] if r["row"] == "p03")
        assert p03["amounts"]["interest"] == "Not stated"


def test_view_cp1_facts_follow_the_head() -> None:
    block = cp1c.context_block(
        pack=_pack("positive"), upstream=_upstream(_cp1_module(_metrics(Decimal(2))))
    )
    facts = block["cp1_facts"]
    assert isinstance(facts, list)
    assert [f["shown"] for f in facts] == ["50.0%", "3.33x", "12.00x", "84.0%"]
    unsettled = cp1c.context_block(
        pack=_pack("positive"), upstream=_upstream(_cp1_module(_metrics(not_known=True)))
    )
    gaps = unsettled["cp1_facts"]
    assert isinstance(gaps, list)
    assert [f["shown"] for f in gaps] == [None, "1.67x", None, "42.0%"]


def test_view_of_an_unreadable_peer_table_has_no_rows() -> None:
    block = cp1c.context_block(pack=_pack("unparseable", base="positive"), upstream=_upstream())
    peers = block["peers"]
    assert isinstance(peers, dict)
    assert (peers["state"], peers["rows"], peers["issuer_line"]) == ("present", [], None)


# --- a real store, built fast (no CP-1 promotion): submit, settle, probe, view ------------------


def _command(module_id: str) -> Fact:
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


def _settled_store(
    tmp_path: Path,
    case: str,
    metrics: dict[str, Fact] | None = None,
    as_of: datetime.date | None = None,
) -> tuple[Execution, str]:
    """CP-0 and CP-1 settled in a real store (hand-built modules through `begin`/`finish`), then
    CP-1C begun. Returns the store and the CP-1C ticket."""
    pack = _pack(case, as_of=as_of)
    store = Execution.create(tmp_path / "store", pack)
    cp0_ticket = store.begin("CP-0")
    cp0 = _cp0_module(pack.run.as_of).model_copy(
        update={
            "status": "candidate",
            "inputs": cp0_ticket.inputs,
            "run_id": pack.run.run_id,
            "facts": (_command("CP-1"), _command(MODULE)),
        }
    )
    store.finish(cp0_ticket.ticket_id, cp0.model_dump_json(), lambda _m: ())
    cp1_ticket = store.begin("CP-1")
    cp1 = _cp1_module(
        _metrics(cited=True) if metrics is None else metrics, as_of=pack.run.as_of
    ).model_copy(
        update={"status": "candidate", "inputs": cp1_ticket.inputs, "run_id": pack.run.run_id}
    )
    store.finish(cp1_ticket.ticket_id, cp1.model_dump_json(), lambda _m: ())
    return store, store.begin(MODULE).ticket_id


def _read_all(text: str) -> Seen:
    return Seen(read=frozenset(cited_locators(text)))


def _submit(store: Execution, ticket: str, payload: str, seen: Seen | None = None) -> Any:
    sight = _read_all(payload) if seen is None else seen
    return cp1c.submit(store, ticket, STEP, payload, lambda text: cp1c.RULES(text, sight))


def _head(store: Execution, module_id: str = MODULE) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


@pytest.mark.parametrize(
    ("case", "as_of"),
    [("positive", None), ("gap", datetime.date(2026, 2, 1)), ("no_peers", None)],
)
def test_submit_settles_the_head_and_the_probe_accepts_it(
    tmp_path: Path, case: str, as_of: datetime.date | None
) -> None:
    store, ticket = _settled_store(tmp_path, case, as_of=as_of)
    payload = json.dumps(_payload(case))
    submitted = _submit(store, ticket, payload)
    assert submitted.journal.status == "finished" and submitted.journal.issues == ()
    snapshot = store.read()
    head = _head(store)
    assert head.status == stage1.expected()["cases"][case]["module_status"]
    settled = store.head_module(head)
    assert settled.as_of == (as_of or AS_OF)
    tail = settled.inputs[-1]
    assert (tail.input_id, tail.sha256) == (
        "peer-benchmark-submission",
        _submission(case).content_hash(),
    )
    assert list(settled.limitations) == stage1.expected()["cases"][case]["settled_limitations"]
    assert settled.inherited_limitations == ("CP-0 note", "CP-1 note")
    cp1c.probe(store, snapshot, submitted.journal)  # rebuilds exactly, writes nothing
    assert store.read() == snapshot


def test_probe_raises_identity_mismatch_when_the_journal_does_not_rebuild(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    payload = json.dumps(_payload())
    done = _submit(store, ticket, payload)
    snapshot = store.read()
    step = done.journal.steps[0]
    other = json.loads(payload)
    other["overall"]["rationale"] += " Reviewed."
    forged = done.journal.model_copy(
        update={
            "steps": (step.model_copy(update={"payload_sha256": store._store(json.dumps(other))}),)
        }
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp1c.probe(store, snapshot, forged)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp1c.probe(store, snapshot, done.journal.model_copy(update={"steps": (step, step)}))


def test_two_r04_attempts_settle_blocked_with_limitations_only(tmp_path: Path) -> None:
    blocked = stage1.expected()["blocked"]
    assert (blocked["attempt_0"], blocked["attempt_1"]) == ("r04", "r04")
    literal = next(r for r in stage1.submissions()["refusals"] if r["id"] == "r04")
    store, ticket = _settled_store(tmp_path, literal["pack"])
    payload = json.dumps(literal["payload"])
    first = _submit(store, ticket, payload)
    assert first.journal.status == "finished" and first.journal.issues
    second = _submit(store, store.begin(MODULE).ticket_id, payload)
    head = _head(store)
    assert head.status == blocked["head_status"] and second.journal.number == 1
    module = store.head_module(head)
    assert module.tables == () and module.facts == ()
    assert blocked["limitations_contain"] in module.limitations


def test_unread_page_is_a_journaled_invalid_step(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    refusal = next(t for t in stage1.expected()["tool_refusals"] if t["id"] == "t01")
    done = _submit(store, ticket, json.dumps(_payload()), Seen())
    assert done.journal.status == "finished"
    assert done.journal.issues == tuple(refusal["expected_issues"])
    assert not any(h.module_id == MODULE and h.status != "blocked" for h in store.read().heads)


def test_submit_refuses_a_foreign_step(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    with pytest.raises(ValueError, match="CP-1C has one step"):
        cp1c.submit(store, ticket, "earnings_quality", json.dumps(_payload()), None)


def test_entry_validator_is_the_one_submit_journals_with(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    done = _submit(store, ticket, json.dumps(_payload()))
    outcome = cp1c.ENTRY_VALIDATOR(store, store.pack(), done.journal)
    assert outcome.issues == () and outcome.retained_as(done.journal.steps[0])


def test_upstream_binds_the_attempt_and_a_stale_store_is_one_issue(tmp_path: Path) -> None:
    """`cp1c_upstream` reads the bound heads and the inputs now; with the CP-1 head gone from the
    snapshot `current_inputs` refuses, and that text is the one issue (no content check runs)."""
    store, ticket = _settled_store(tmp_path, "positive")
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    up = cp1c.cp1c_upstream(store, attempt)
    assert up.bound == attempt.inputs and up.current == attempt.inputs
    assert up.inherited == ("CP-0 note", SYNTHETIC, "CP-1 note")
    assert (up.cp0.module_id, up.cp1.module_id) == ("CP-0", "CP-1")
    snapshot = store.read()
    heads = tuple(h for h in snapshot.heads if h.module_id != "CP-1")
    stale = cp1c.cp1c_upstream(
        _FrozenExecution(store, snapshot.model_copy(update={"heads": heads})), attempt
    )
    assert stale.current == "Required upstream is unrun, stale or blocked"
    high = _payload()
    high["overall"]["confidence"] = "High"
    for body in (_payload(), high):
        assert cp1c.validate_peer_benchmark(
            pack=store.pack(), submission=_submission(payload=body), upstream=stale
        ) == ("Stale inputs: Required upstream is unrun, stale or blocked",)


def test_a_bound_input_of_another_module_raises(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    cp0 = next(i for i in attempt.inputs if i.input_id == "CP-0")
    forged = attempt.model_copy(
        update={
            "inputs": tuple(
                i.model_copy(update={"sha256": cp0.sha256}) if i.input_id == "CP-1" else i
                for i in attempt.inputs
            )
        }
    )
    with pytest.raises(ValueError, match="CP-1 input is a CP-0 module"):
        cp1c.cp1c_upstream(store, forged)
    alone = attempt.model_copy(update={"inputs": (cp0,)})
    with pytest.raises(ValueError, match="binds no CP-1 input"):
        cp1c.cp1c_upstream(store, alone)


def test_view_over_a_real_store_is_the_context_block(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    digest, body = cp1c.view(store, attempt)
    assert hashlib.sha256(body.encode()).hexdigest() == digest
    assert body == json.dumps(json.loads(body), ensure_ascii=False, separators=(",", ":"))
    block = json.loads(body)
    assert block == json.loads(
        json.dumps(
            cp1c.context_block(pack=store.pack(), upstream=cp1c.cp1c_upstream(store, attempt))
        )
    )
    assert block["inherited_limitations"] == ["CP-0 note", SYNTHETIC, "CP-1 note"]
    assert [u["module_id"] for u in block["upstream"]] == ["CP-0", "CP-1"]


class _Fresh:
    """A `ReviewRun` over a fast real store at the CP-1C step: each `submit_review` begins the
    repair attempt when the last one finished, reads every cited page, and submits through
    `cp1c.submit` (the module's real submit path)."""

    root: Path
    count = 0

    def __init__(self) -> None:
        _Fresh.count += 1
        self.store, self.ticket = _settled_store(_Fresh.root / f"run{_Fresh.count}", "positive")

    def submit_review(self, payload: str) -> dict[str, Any]:
        attempt = next(a for a in self.store.read().attempts if a.ticket_id == self.ticket)
        if attempt.status != "pending":
            self.ticket = self.store.begin(MODULE).ticket_id
        done = _submit(self.store, self.ticket, payload)
        valid = done.journal.status == "finished" and not done.journal.issues
        return {"status": "valid" if valid else "invalid", "issues": list(done.journal.issues)}


def test_model_text_at_the_submit_path_never_raises_or_wedges(tmp_path: Path) -> None:
    """Round 3 item 2 and round 5 item 10 over the real submit path: nothing raises after the
    binding write, every non-verbatim path journals an issue, and the run is not wedged."""
    _Fresh.root = tmp_path
    failures = model_text_failures(
        cp1c.PeerBenchmarkSubmission, json.dumps(_payload()), _Fresh, verbatim=CP1C_VERBATIM
    )
    assert failures == []


# --- registrations (lease Files; append-only rows) -----------------------------------------------


def test_registrations_equal_the_lease() -> None:
    expected = owner.OwnerSpec(
        module_id=MODULE,
        steps=(
            owner.StepSpec(
                step_id=STEP,
                schema=cp1c.PeerBenchmarkSubmission,
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
    assert owner.OWNER_SPECS[MODULE] == expected
    assert MODULE in owner.SUPPORTED_ANALYTICAL
    assert owner._CORES[MODULE] is cp1c
    assert owner._QUALIFICATION[MODULE] is cp1c.QUALIFICATION
    assert owner._PROBES[MODULE] is cp1c.probe
    assert owner._VIEWS[STEP] is cp1c.view
    assert owner._ENTRY_VALIDATORS[MODULE] is cp1c.ENTRY_VALIDATOR
    assert MODULE not in owner._PRECHECKS
    owner._check_steps(MODULE, owner.OWNER_SPECS[MODULE])


def test_sources_flag_matches_the_h1_owner_scope_row() -> None:
    """G1-X guard: `sources` agrees with the `_OWNER_SCOPES` row, which keeps the module's scope."""
    row = host._OWNER_SCOPES[(MODULE, STEP)]
    for case in CASES:
        pack = _pack(case)
        assert row(pack) == tuple(s.source_id for s in pack.sources if s.source_id in cp1c.SCOPE)
    wrong = dataclasses.replace(owner.OWNER_SPECS[MODULE].steps[0], sources=False)
    with pytest.raises(WorkflowError):
        owner._check_steps(MODULE, dataclasses.replace(owner.OWNER_SPECS[MODULE], steps=(wrong,)))


def test_registrations_are_appended_after_their_dependencies() -> None:
    """Append-only: the shipped prefix stands, and each CP-1C row comes after the rows merged
    before it (CP-2G, the previous batch module). Later appends are not this test's."""
    assert tuple(owner.OWNER_SPECS)[:5] == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._QUALIFICATION)[:4] == ("CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._PROBES)[:4] == ("CP-0", "CP-1", "CP-1A", "CP-2")
    assert tuple(owner._VIEWS)[:1] == ("credit_synthesis",)
    assert tuple(owner._ENTRY_VALIDATORS)[:2] == ("CP-1A", "CP-2")
    assert tuple(owner._CORES)[:2] == ("CP-DR", "CP-3D")
    for table, key, after in (
        (owner.OWNER_SPECS, MODULE, ("CP-0", "CP-1", "CP-2G")),
        (owner._CORES, MODULE, ("CP-2G",)),
        (owner._QUALIFICATION, MODULE, ("CP-1", "CP-2G")),
        (owner._PROBES, MODULE, ("CP-0", "CP-1", "CP-2G")),
        (owner._ENTRY_VALIDATORS, MODULE, ("CP-2G",)),
        (owner._VIEWS, STEP, ("forward_credit_model",)),
    ):
        order = list(table)
        assert all(order.index(key) > order.index(a) for a in after), (key, after)
    analytical = sorted(owner.SUPPORTED_ANALYTICAL)
    assert {"CP-0", "CP-1", MODULE} <= set(analytical)


@pytest.mark.parametrize("case", CASES)
def test_a_plan_with_cp1c_passes_check_specs(case: str, tmp_path: Path) -> None:
    planned = owner._check_specs(_pack(case), owner.OWNER_SPECS, None, tmp_path / case)
    assert list(planned) == stage1.expected()["execution"]["plan_order"]


# --- bindings and the _Spec row (lease D7) ----------------------------------------------------------

BLOCK = "peer-positioning"


def test_spec_row_is_appended_to_the_relative_value_composition() -> None:
    fp03 = stage1.expected()["cases"]["positive"]["FP03"]["blocks"][BLOCK]
    spec = _spec_of(BLOCK)
    assert _RELATIVE_VALUE[BLOCK] is spec
    assert (spec.title, spec.owner, spec.kind, spec.producers, spec.route_label) == (
        fp03["title"],
        fp03["owner"],
        fp03["kind"],
        (MODULE,),
        "Full analysis",
    )
    keys = list(_RELATIVE_VALUE)
    assert keys[0] == "market-against-fundamentals"
    assert keys.index(BLOCK) > keys.index("market-against-fundamentals")
    preset = next(p for p in pathways() if p.id == "relative_value").blocks
    assert BLOCK in preset


def test_shipped_maps_hold_cp1c_once_after_its_producers() -> None:
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.count(MODULE) == 1
    assert ids.index(MODULE) > max(ids.index("CP-0"), ids.index("CP-1"), ids.index("CP-2G"))


def _view(case: str, module: Module, mode: Literal["candidate", "accepted"] = "candidate") -> View:
    pack = _pack(case)
    return View(
        run=pack.run,
        mode=mode,
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Peer benchmark",
                aliases=(),
                status=stage1.expected()["cases"][case]["module_status"],
                artifact_sha256="a" * 64,
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )


@pytest.mark.parametrize("case", CASES)
def test_bindings_place_every_fp03_table_exactly_once(case: str) -> None:
    module = _module(case)
    cp1c_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    assert validate_bindings(_view(case, module), SHIPPED_MAPS) == ()
    by_table = {e.fact_coord.table_id: e for e in cp1c_map.entries}
    assert len(by_table) == len(cp1c_map.entries)
    fp03 = stage1.expected()["cases"][case]["FP03"]
    tabs = fp03["blocks"][BLOCK]["tabs"]
    assert [(e.fact_coord.table_id, e.label) for e in cp1c_map.entries if e.block_id == BLOCK] == [
        (t["table_id"], t["label"]) for t in tabs
    ]
    assert [t for t, e in by_table.items() if e.block_id == "evidence"] == fp03[
        "evidence_rail_tables"
    ]
    assert [t for t, e in by_table.items() if e.block_id == "limitations"] == fp03[
        "limitations_rail_tables"
    ]
    assert set(by_table) == {t.table_id for t in module.tables}
    assert all(e.cell_slot.startswith("cp1c-") for e in cp1c_map.entries)
    assert all(e.fact_coord.module_id == MODULE for e in cp1c_map.entries)


@pytest.mark.parametrize("case", CASES)
def test_binding_unit_class_is_the_one_class_its_table_displays(case: str) -> None:
    """The bindings' rule (bindings/cp1c.py): a table whose facts all display in one unit class
    is bound with it; a table mixing classes, or holding exact-text units, is bound as text."""
    module = _module(case)
    facts = {f.fact_id: f for f in module.facts}
    tables = {t.table_id: t for t in module.tables}
    cp1c_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    for entry in cp1c_map.entries:
        assert entry.fact_coord.table_id is not None
        table = tables[entry.fact_coord.table_id]
        shown = {_unit_class(facts[f].unit) for row in table.rows for f in row.fact_ids}
        want = next(iter(shown)) if len(shown) == 1 and None not in shown else "text"
        assert entry.unit_class == want, table.table_id


@pytest.mark.parametrize("case", CASES)
def test_fp03_heads_and_tab_labels_equal_the_oracle(case: str) -> None:
    """`report_view.build` over the shipped maps, relative_value, every other module unrun."""
    module = _module(case)
    only = _view(case, module, mode="accepted")
    others = tuple(
        ModuleView(module_id=m.module_id, title=m.module_id, aliases=(), status="unrun")
        for m in SHIPPED_MAPS
        if m.module_id != MODULE
    )
    view = only.model_copy(update={"modules": (*only.modules, *others)})
    pathway = next(p for p in pathways() if p.id == "relative_value")
    blocks = {b.block_id: b for b in build(view, pathway, SHIPPED_MAPS).blocks}
    want = stage1.expected()["cases"][case]["FP03"]["blocks"][BLOCK]
    block = blocks[BLOCK]
    assert (block.title, block.owner, block.kind, block.state) == (
        want["title"],
        want["owner"],
        want["kind"],
        want["state"],
    )
    assert [block.tab_label, *(t.label for t in block.tabs)] == [t["label"] for t in want["tabs"]]


@pytest.mark.parametrize("case", CASES)
def test_fp03_cells_are_the_settled_spellings(case: str) -> None:
    assert_fp03_cells(case, _module(case))


def assert_fp03_cells(case: str, module: Module) -> None:
    """Every FP03 tab row and cell of the case: row ids, labels, fact ids, spelled state, and the
    shown text of a known cell (`expected.json cases.<case>.FP03`)."""
    facts = {f.fact_id: f for f in module.facts}
    tables = {t.table_id: t for t in module.tables}
    for tab in stage1.expected()["cases"][case]["FP03"]["blocks"][BLOCK]["tabs"]:
        table = tables[tab["table_id"]]
        assert [r.row_id for r in table.rows] == [r["row_id"] for r in tab["rows"]]
        for row, want in zip(table.rows, tab["rows"], strict=True):
            assert row.label == want["label"]
            assert list(row.fact_ids) == [c["fact_id"] for c in want["cells"]]
            for fid, cell in zip(row.fact_ids, want["cells"], strict=True):
                fact = facts[fid]
                _, state, text = fact_spelling(fact, "G1")
                assert state == cell["state"], fid
                if fact.status == "known":
                    assert text == cell["shown"], fid


# --- the reader the lease names for a consumer (Public API, D3 open) -----------------------------


def _pinned() -> list[str]:
    return [
        *(
            f"T1C.4.{m.key}.{name}"
            for m in cp1c.METRICS
            for name in ("median", "difference", "position", "outlier_count")
        ),
        "T1C.8.total.included",
    ]


def test_reader_pins_the_consumption_facts_of_the_oracle() -> None:
    pinned = stage1.expected()["execution"]["consumption"]["consumer_facts"]
    metric_fields = [p.split(".")[-1] for p in pinned if p.startswith("T1C.4.<metric>.")]
    assert metric_fields == ["median", "difference", "position", "outlier_count"]
    assert pinned[-1] == "T1C.8.total.included"
    assert list(cp1c.READER_FACTS) == _pinned()


@pytest.mark.parametrize("case", CASES)
def test_reader_exposes_what_the_lease_pins(case: str, tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, case)
    _submit(store, ticket, json.dumps(_payload(case)))
    head = _head(store)
    module = store.head_module(head)
    facts = {f.fact_id: f for f in module.facts}
    read = cp1c.cp1c_reader(store, head)
    assert (read.status, read.head_sha256) == (head.status, head.result_sha256)
    assert read.limitations == module.limitations and read.limitations[-1] == SYNTHETIC
    assert [f.fact_id for f in read.facts] == _pinned()
    assert all(f == facts[f.fact_id] for f in read.facts)
    if case == "positive":
        tamper = stage1.expected()["tamper"]
        assert read.fact(tamper["target_fact"]).amount == Decimal(2)
    with pytest.raises(ValueError, match="not exposed"):
        read.fact("T1C.5.p01.ffo_to_debt_flag")


def test_reader_follows_the_head_not_the_oracle(tmp_path: Path) -> None:
    metrics = _metrics(cited=True)
    metrics["total_leverage_adjusted"] = metrics["total_leverage_adjusted"].model_copy(
        update={"amount": Decimal("2.5")}
    )
    store, ticket = _settled_store(tmp_path, "positive", metrics)
    _submit(store, ticket, json.dumps(_payload()))
    read = cp1c.cp1c_reader(store, _head(store))
    assert read.fact("T1C.4.total_leverage_adjusted.position").amount == Decimal(3)
    assert read.fact("T1C.4.total_leverage_adjusted.difference").amount == Decimal(0)


def test_reader_of_a_blocked_head_is_status_and_hash_only(tmp_path: Path) -> None:
    literal = next(r for r in stage1.submissions()["refusals"] if r["id"] == "r04")
    store, ticket = _settled_store(tmp_path, "positive")
    _submit(store, ticket, json.dumps(literal["payload"]))
    _submit(store, store.begin(MODULE).ticket_id, json.dumps(literal["payload"]))
    head = _head(store)
    assert cp1c.cp1c_reader(store, head) == cp1c.Cp1cHead(
        status="blocked", head_sha256=head.result_sha256
    )


def test_reader_refuses_another_module_and_a_stale_head(tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    _submit(store, ticket, json.dumps(_payload()))
    with pytest.raises(ValueError, match="not a CP-1C head"):
        cp1c.cp1c_reader(store, _head(store, "CP-1"))
    stale = _head(store).model_copy(update={"status": "stale"})
    with pytest.raises(ValueError, match="CP-1C head is stale"):
        cp1c.cp1c_reader(store, stale)


@pytest.mark.parametrize("fact_id", ["T1C.4.ffo_to_debt.outlier_count", "T1C.8.total.included"])
def test_reader_refuses_a_head_without_a_pinned_fact(fact_id: str, tmp_path: Path) -> None:
    store, ticket = _settled_store(tmp_path, "positive")
    _submit(store, ticket, json.dumps(_payload()))
    head = _head(store)
    module = store.head_module(head)
    forged = module.model_copy(  # the tables go too: a cell may not name an unknown fact
        update={"facts": tuple(f for f in module.facts if f.fact_id != fact_id), "tables": ()}
    )
    digest = store._store(Module.model_validate(forged.model_dump()).model_dump_json())
    with pytest.raises(ValueError, match=f"the head has no fact {fact_id}$"):
        cp1c.cp1c_reader(store, head.model_copy(update={"result_sha256": digest}))


def test_d3_stays_open_and_no_consumer_reads_cp1c() -> None:
    """Lease D3: no consumer exists. The shipped CP-3 and CP-6 cores do not read CP-1C, no other
    owner core calls the reader, and the oracle's consumption status is open."""
    from deploy_vii import cp3_relative_value, cp6_committee

    assert MODULE not in cp3_relative_value.READ_OPTIONAL
    assert MODULE not in cp6_committee.READ_OPTIONAL
    owners_dir = ROOT / "src" / "deploy_workflow" / "owners"
    readers = [p.name for p in owners_dir.glob("*.py") if "cp1c_reader" in p.read_text()]
    assert readers == ["cp1c.py"]
    assert stage1.expected()["execution"]["consumption"]["status"].startswith("open")


# --- D8 table ids (lease Acceptance A7; the methodology register has landed) ---------------------


def test_d8_t1c_table_ids_are_registered_once_and_every_case_validates() -> None:
    ids = [t for m in registry.modules() for t in m.table_ids]
    mine = next(m for m in registry.modules() if m.module_id == MODULE).table_ids
    assert sorted(mine) == stage1.expected()["d8_table_ids"]["proposed_ids"]
    assert all(ids.count(t) == 1 for t in mine)
    for case in CASES:
        module = _module(case)
        validate_tables(module.tables, module.facts)  # raises on a layout mismatch
        assert {t.table_id for t in module.tables} <= set(mine)


# --- the run driver's non-promotion helpers (`tests/cp1c_runs.py`; its runs are Stage 5) ---------


@pytest.mark.parametrize("case", runs.CASES)
def test_driver_pack_is_the_case_run_over_the_hash_checked_sources(case: str) -> None:
    pack = runs.make_pack(case)
    base = "positive" if case == "blocked" else case
    assert pack.run.run_id == stage1.manifest()["cases"][base]["run"]["run_id"]
    by_id = {s.source_id: s for s in pack.sources}
    assert set(by_id) == (
        {"identity", "financial", "peers"} if base in runs.PEERS else {"identity", "financial"}
    )
    assert (by_id["financial"].status == "missing") == (case == "refused")
    if "peers" in by_id:
        synthetic = stage1.manifest()["synthetic_source"]
        assert by_id["peers"].sha256 == synthetic[base]["sha256"]
        assert by_id["peers"].limitation == synthetic["pack_limitation"]


def test_driver_cp0_literals_bind_the_pack_and_the_refused_row() -> None:
    pack = runs.make_pack("positive")
    text = runs.cp0_review(pack, "positive")
    assert (
        runs.PACK_PLACEHOLDER not in text and json.loads(text)["pack_sha256"] == pack.content_hash()
    )
    refused = json.loads(runs.cp0_review(runs.make_pack("refused"), "refused"))
    rows = stage1.submissions()["refused"]
    assert [c["module_id"] for c in refused["consumers"]] == ["CP-1", "CP-1C"]
    assert refused["consumers"][-1] == rows["cp0_consumer_row_cp1c"]
    assert refused["gaps"] == [rows["gap_row"]]


def _catalogue(rules: dict[str, str], *, doubled: str | None = None) -> Any:
    """Readiness inputs with one record per `{{EVID:*}}` predicate (twice for `doubled`) and a
    decoy of each kind whose field values differ."""
    records = []
    for marker, rule in rules.items():
        match = runs.BINDING.match(rule)
        if match is None:
            continue
        fields = dict(runs.CONDITION.findall(match[2]))
        decoy = {k: f"{v}-other" for k, v in fields.items()}
        name = marker.strip("{}")  # an id of the record, not a marker
        for evidence_id, values in ((f"ev-{name}", fields), (f"decoy-{name}", decoy)):
            records.append(
                SimpleNamespace(
                    evidence_id=evidence_id, kind=match[1], record_json=json.dumps(values)
                )
            )
        if marker == doubled:
            records.append(records[-2])
    gaps = (SimpleNamespace(gap_id="gap-a"), SimpleNamespace(gap_id="gap-b"))
    inputs = SimpleNamespace(catalogue=tuple(records))
    return SimpleNamespace(narrative=SimpleNamespace(inputs=inputs, gaps=gaps))


@pytest.mark.parametrize("case", CASES)
def test_driver_binds_every_readiness_marker_by_its_oracle_predicate(
    case: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    readiness = stage1.submissions()[case]["cp1_readiness"]
    rules = readiness["run_time_bindings"]
    evid = [m for m in rules if m.startswith("{{EVID:")]
    assert all(runs.BINDING.match(rules[m]) for m in evid)
    monkeypatch.setattr(
        runs._driver("cp1d_runs"), "downstream_inputs", lambda _w: _catalogue(rules)
    )
    bound = json.loads(runs.readiness_literal(cast(Any, None), case))
    assert "inputs_sha256" not in bound and "{{" not in json.dumps(bound)
    literal = readiness["payload"]["consumers"]
    for got, want in zip(bound["consumers"], literal, strict=True):
        for g, w in zip(got["requirements"], want["requirements"], strict=True):
            assert g["evidence_ids"] == [f"ev-{m.strip('{}')}" for m in w["evidence_ids"]]
        assert [s["gap_ids"] for s in got["gaps"]] == [["gap-a", "gap-b"]] * len(want["gaps"])
    monkeypatch.setattr(
        runs._driver("cp1d_runs"),
        "downstream_inputs",
        lambda _w: _catalogue(rules, doubled=evid[0]),
    )
    with pytest.raises(RuntimeError, match="2 catalogue records, expected exactly one"):
        runs.readiness_literal(cast(Any, None), case)
