"""CP-2H Stage 2: the connection of the Stage 1 core to the store, the registrations, the
bindings and the fast consumption proof for CP-2G (`docs/CP2H-OWNER-LEASE.md`,
`docs/G1X-OWNER-CORE-PROTOCOL.md`).

Expectations come from the lease and `cases/cp2h-owner/{expected,submissions,manifest}.json`
(with the pinned CP-2G oracle), never from the code under test. The stores here are real
`Execution` stores: CP-0, CP-1 and CP-2A are settled through `begin`/`finish` from the oracles'
own records, and CP-2G through the real CP-2G core on its frozen gap literal, so no CP-1
promotion runs (the genuine runs are `tests/test_owner_cp2h.py` and `tests/cp2h_runs.py`). The
fixtures vary the CP-1 ratios, the as-of date, the case kind (heads settle accepted or
restricted) and the agency source, so a constant equal to the oracle cannot pass.
"""

import copy
import hashlib
import importlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pytest
import test_method_cp2g as cp2g_stage1
import test_method_cp2h as stage1
import view_tree
from defect_classes import (
    MODEL_TEXT_HOSTILE,
    assert_hostile_refused,
    free_text_paths,
    path_matches,
    with_text,
)
from test_connect_cp8 import _payload_facts, _what_changed_view

from deploy_vii import prose
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import (
    Citation,
    Fact,
    Input,
    Module,
    ModuleView,
    ReportTable,
    Run,
    TableColumn,
    TableRow,
    View,
)
from deploy_vii.execution import Attempt, Execution, Head, Qualification
from deploy_vii.live.tools import Seen, cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import _DISTRESSED, _PRESETS, _spec_of, fact_spelling
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.owners import cp2g, cp2h
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")

MODULE = "CP-2H"
STEP = "rating_triggers"
SYNTHETIC = "Synthetic case; not real issuer qualification"
EXPECTED = stage1.EXPECTED
SUBMISSIONS = stage1.SUBMISSIONS
MANIFEST = stage1.MANIFEST
CaseKind = Literal["public", "private", "synthetic"]

MAX_LINE = 600
LONG = "7" * 5000


def _payload(case: str = "positive") -> dict[str, Any]:
    payload: dict[str, Any] = copy.deepcopy(stage1.raw_payload(case))
    return payload


def _issues(payload: dict[str, Any], case: str = "positive") -> tuple[str, ...]:
    return cp2h.validate(stage1.inputs(case, payload))


# --- backlog (stage2-backlog.md "Every module" and the CP-2H rows; protocol section 6) ----------


@pytest.mark.parametrize("blank", [" ", "  ", "\u200b", "\ufeff", "\n\t", " \u00ad "])
@pytest.mark.parametrize(("view", "cite"), [(0, 0), (1, 0), (0, 2)])
def test_a_blank_citation_quote_is_empty_text_before_the_page_check(
    view: int, cite: int, blank: str
) -> None:
    """Round 13 addendum 3 (backlog "Every module"): a quote that `is_blank` gets the pinned
    `<path>: empty text` frame at the citation step, before the page-occurrence check. Inventory:
    before this, a blank quote was refused only as a page mismatch (fail closed, no Medium)."""
    payload = _payload()
    payload["views"][view]["evidence"][cite]["quote"] = blank
    assert _issues(payload) == (f"views[{view}].evidence[{cite}].quote: empty text",)


def _clipped(issues: tuple[str, ...], prefix: str) -> None:
    hit = [i for i in issues if i.startswith(prefix)]
    assert hit, (prefix, issues)
    assert all(len(i) <= MAX_LINE for i in issues), [len(i) for i in issues]


def test_an_unknown_agency_line_is_clipped() -> None:
    """Protocol section 6, 0d-c audit (cp2h `v.agency`): the line quotes the analyst's agency."""
    payload = _payload()
    payload["views"][0]["agency"] = "Zeta " + "Z" * 5000
    _clipped(_issues(payload), "views[0].agency: not an agency in the rating register: Zeta ZZ")


@pytest.mark.parametrize("field", ["rationale", "limitation"])
def test_a_prose_issue_line_is_clipped(field: str) -> None:
    """0d-c audit (cp2h `prose.issues`/`prose.check` lines): the line quotes the figure."""
    payload = _payload()
    payload["views"][0][field] = f"A figure of {LONG} appears."
    _clipped(_issues(payload), f"views[0].{field}: Bare figure: 7777")


def test_a_citation_issue_line_is_clipped() -> None:
    """0d-c audit (cp2h `citation_issues` lines): a mismatch line quotes the locator."""
    payload = _payload()
    payload["views"][0]["evidence"][0]["locator"] = "page:" + "9" * 5000
    _clipped(_issues(payload), "views[0].evidence[0]: Quote/locator mismatch")


def _over(edits: list[tuple[int, str, str]]) -> cp2h.TriggerInputs:
    return stage1._over(stage1.inputs("positive"), stage1._edited("positive", edits))


def test_source_issue_lines_quoting_the_page_are_clipped() -> None:
    """0d-c audit (cp2h `Rating not on the scale` and `Unrecognised trigger metric` lines): the
    agency source is pack text, so its quoted rating or metric is clipped too."""
    off = _over([(0, "BB  Negative", "B" * 5000 + "  Negative")])
    (issue,) = cp2h.validate(off)
    assert issue.startswith("Rating not on the scale: Alder Ratings BBB") and len(issue) <= MAX_LINE
    odd = _over([(2, "Free cash flow to total debt", "F" * 5000)])
    (issue,) = cp2h.validate(odd)
    assert issue.startswith("Unrecognised trigger metric: FFF") and len(issue) <= MAX_LINE


def test_a_refused_current_inputs_text_is_one_clipped_stale_issue() -> None:
    (issue,) = cp2h.stale_issues(bound=stage1.BOUND, current="Required upstream " + "x" * 5000)
    assert issue.startswith("Stale inputs: Required upstream") and len(issue) <= MAX_LINE


def test_the_message_of_a_refused_composition_is_bounded() -> None:
    """0d-c audit (the cp2h `"; ".join(issues)`): `compute` raises the bounded list, 20 lines and
    a count of the rest."""
    payload = _payload()
    gap = payload["gaps"][0]
    blank = {"gap": " ", "why_it_matters": " ", "affected_analysis": " "}
    payload["gaps"] = [dict(gap, **blank) for _ in range(8)]
    case_inputs = stage1.inputs("positive", payload)
    assert len(cp2h.validate(case_inputs)) == 24
    with pytest.raises(ValueError) as caught:
        cp2h.compute(case_inputs)
    assert str(caught.value).endswith("; 4 further issues not listed")  # 20 shown of 24


@pytest.mark.parametrize("path", [("views", 0, "rationale"), ("overall", "rationale")])
def test_claim_text_is_checked_with_the_type_the_claim_builds(
    path: tuple[str | int, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stage 2 round 3 item 2: a rationale becomes `Claim.text` (`RunText`); if `prose.issues`
    ever passed text `RunText` refuses, the validator still journals the type's own message
    (`include_input=False`), so nothing raises after the binding write."""
    monkeypatch.setattr(prose, "issues", lambda text, bound, names=(): ())
    payload = _payload()
    node: Any = payload
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = "{low"
    where = ".".join(str(k) for k in path).replace(".0.", "[0].")
    assert _issues(payload) == (
        f"{where}: Value error, Malformed run text: unbalanced or empty reference",
    )


def test_payload_text_is_parsed_through_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protocol section 6 (the cp2h `payload_issues` rewire): the schema validates the bounded
    `json_object` document's exact re-serialisation, never the raw text; text `json_object`
    refuses keeps its frozen shape issue."""
    seen: list[str] = []
    real = cp2h.TriggerSubmission.model_validate_json

    def spy(text: str | bytes, **kwargs: Any) -> cp2h.TriggerSubmission:
        seen.append(str(text))
        return real(text, **kwargs)

    monkeypatch.setattr(cp2h.TriggerSubmission, "model_validate_json", spy)
    case_inputs = stage1.inputs("positive")
    spaced = json.dumps(json.loads(case_inputs.submission.model_dump_json()), indent=2)
    up, pack = case_inputs.upstream, case_inputs.pack
    assert cp2h.payload_issues(spaced, pack=pack, upstream=up) == ()
    assert seen and spaced not in seen
    r06 = stage1.SUBMITTED["r06"]["payload_text"]
    assert cp2h.payload_issues(r06, pack=pack, upstream=up) == (
        "(root): Invalid JSON: key must be a string at line 1 column 2",
    )
    for hostile in ('{"a": "\\ud800"}', "[" * 5000 + "]" * 5000, '{"x": NaN}'):
        issues = cp2h.payload_issues(hostile, pack=pack, upstream=up)
        assert issues and all(len(i) <= MAX_LINE for i in issues)


# --- the plug-in parts that need no store (protocol section 2) ---------------------------------


def test_core_attributes_match_the_lease() -> None:
    assert (cp2h.MODULE_ID, cp2h.STEP_ID, cp2h.SCHEMA_VERSION) == (
        MODULE,
        STEP,
        "rating-triggers/1",
    )
    assert cp2h.QUALIFICATION == Qualification(implementation="implemented")
    assert cp2h.STEP_IDS == (STEP,)
    assert dict(cp2h.SCHEMAS) == {STEP: cp2h.TriggerSubmission}
    assert cp2h.SUBMISSION_INPUT == "rating-triggers-submission"
    assert cp2h.RatingTriggersReport.model_fields["schema_version"].default == cp2h.SCHEMA_VERSION
    for name in ("probe", "view", "submit", "ENTRY_VALIDATOR", "RULES", "cp2h_upstream"):
        assert callable(getattr(cp2h, name)), name
    for name in ("validate_triggers", "rating_triggers", "context_block", "cp2h_module"):
        assert callable(getattr(cp2h, name)), name
    # No precheck and no reader of its own (lease Files, Public API).
    assert not hasattr(cp2h, "precheck") and not hasattr(cp2h, "cp2h_reader")


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_schemas_round_trip_and_give_the_tail_digest(case: str) -> None:
    parsed = stage1.inputs(case).submission
    schema = cp2h.SCHEMAS[STEP]
    assert schema.model_validate_json(parsed.model_dump_json()) == parsed
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()


def test_rules_are_the_cited_page_rule_alone() -> None:
    """t01 (submissions.json tool_refusals): the positive payload with no page read gives the
    two unread-page lines; reading both pages clears it; malformed text never raises."""
    payload = stage1.inputs("positive").submission.model_dump_json()
    t01 = next(t for t in SUBMISSIONS["tool_refusals"] if t["id"] == "t01")
    assert list(cp2h.RULES(payload, Seen())) == t01["expected_issues"]
    pages = frozenset({("ratings", "page:1"), ("ratings", "page:3")})
    assert cp2h.RULES(payload, Seen(read=pages)) == ()
    assert list(cp2h.RULES(payload, Seen(read=pages - {("ratings", "page:1")}))) == [
        t01["expected_issues"][0]
    ]
    assert cited_locators(payload) == pages
    assert cp2h.RULES("[1,", Seen()) == ()


# --- a real store, heads settled from the oracles' own records ----------------------------------

CP2G_EXP = stage1.CP2G


def _run(case: str, *, as_of: str | None, case_kind: CaseKind) -> Run:
    # A composer-only fixture has no run of its own: its store runs under the positive run.
    document = dict(MANIFEST["cases"][case]["run"] or MANIFEST["cases"]["positive"]["run"])
    document["case_kind"] = case_kind
    if as_of is not None:
        document["as_of"] = as_of
    return Run.model_validate_json(json.dumps(document))


def _pack(
    case: str = "positive",
    *,
    as_of: str | None = None,
    case_kind: CaseKind = "synthetic",
    variant: str | None = None,
) -> PreparedPack:
    """identity + financial + the case's agency source, and a ready out-of-scope source placed
    before it (the adapter keeps the host scope in pack order and drops the rest)."""
    scope = stage1.pack(stage1.spec(case)[0] if variant is None else variant)
    *frozen, ratings = scope.sources
    press = ratings.model_copy(update={"source_id": "press", "name": "Press cuttings"})
    run = _run(case, as_of=as_of, case_kind=case_kind)
    return PreparedPack(run=run, sources=(*frozen, press, ratings))


def _command(module_id: str) -> Fact:
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


def _finish(
    store: Execution,
    module_id: str,
    facts: tuple[Fact, ...],
    note: str | None,
    tables: tuple[ReportTable, ...] = (),
) -> None:
    ticket = store.begin(module_id)
    run = store.read().run
    module = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        inputs=ticket.inputs,
        facts=facts,
        tables=tables,
        limitations=() if note is None else (note,),
    )
    store.finish(ticket.ticket_id, module.model_dump_json(), lambda _m: ())


def _cp2g_t2h7(cp2g_case: str) -> ReportTable:
    """The oracle's T2H.7 layout: the CP-2G reader takes its break rows from the declared table."""
    t = next(t for t in CP2G_EXP["cases"][cp2g_case]["tables"] if t["table_id"] == "T2H.7")
    fields = [fid.rsplit(".", 1)[1] for fid in t["rows"][0]["fact_ids"]]
    return ReportTable(
        table_id="T2H.7",
        title=t["title"],
        columns=tuple(TableColumn(field=f, label=f) for f in fields),
        rows=tuple(
            TableRow(row_id=r["row_id"], label=r["label"], fact_ids=tuple(r["fact_ids"]))
            for r in t["rows"]
        ),
    )


def _cp2g_facts(cp2g_case: str, cites: dict[str, tuple[Citation, ...]] | None = None) -> Any:
    facts = tuple(stage1._cp2g_fact(r) for r in CP2G_EXP["cases"][cp2g_case]["facts"])
    if not cites:
        return facts
    return tuple(
        f.model_copy(update={"citations": cites[f.fact_id]}) if f.fact_id in cites else f
        for f in facts
    )


def _decoy() -> Fact:
    """A T4.10 fact the CP-2H core never reads (not one of the four reported ratios)."""
    return Fact(
        fact_id="decoy-revenue",
        label=f"{cp2h.LTM_COLUMN} · revenue",
        table_id="T4.10",
        row_id="revenue",
        amount=Decimal(1),
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        period=cp2h.LTM_PERIOD,
        calculation_id="calc:decoy",
    )


def _cp2g_genuine(store: Execution) -> None:
    """The real CP-2G core over the seeded CP-1 and CP-2A heads: its frozen gap literal (the
    closed runs' CP-2G step; manifest cases.*.execution)."""
    ticket = store.begin("CP-2G")
    payload = cp2g_stage1._bind_all(cp2g_stage1._payload("gap"))
    done = cp2g.submit(store, ticket.ticket_id, "forward_credit_model", json.dumps(payload), None)
    assert done.journal.status == "finished" and done.journal.issues == ()


def seed(
    root: Path,
    case: str = "positive",
    *,
    genuine: bool = False,
    cp1_facts: tuple[Fact, ...] | None = None,
    cp2g_cites: dict[str, tuple[Citation, ...]] | None = None,
    as_of: str | None = None,
    case_kind: CaseKind = "synthetic",
    variant: str | None = None,
    notes: bool = True,
) -> tuple[Execution, PreparedPack, Attempt]:
    """A real store with CP-0, CP-1, CP-2A and CP-2G settled and CP-2H begun. By default CP-1
    holds the case's four reported ratios and a decoy, and CP-2G the CP-2G oracle head of the
    case (its records and T2H.7 layout). `genuine` settles CP-1 with the CP-2G oracle's CP-1
    facts, CP-2A from its oracle and CP-2G through the real CP-2G core."""
    pack = _pack(case, as_of=as_of, case_kind=case_kind, variant=variant)
    store = Execution.create(root / "store", pack)

    def note(module_id: str) -> str | None:
        return f"{module_id} note" if notes else None

    _cp2g_case = stage1.spec(case)[1]
    commands = tuple(_command(m) for m in ("CP-1", "CP-2A", "CP-2G", "CP-2H"))
    _finish(store, "CP-0", commands, note("CP-0"))
    if genuine:
        _finish(store, "CP-1", cp2g_stage1._cp1_facts("gap"), note("CP-1"))
        cp2a_facts = tuple(
            cp2g_stage1._fact(r) for r in cp2g_stage1.CP2A_EXP["cases"]["positive"]["facts"]
        )
        _finish(store, "CP-2A", cp2a_facts, note("CP-2A"))
        _cp2g_genuine(store)
    else:
        facts = (*stage1.cp1_facts(_cp2g_case), _decoy()) if cp1_facts is None else cp1_facts
        _finish(store, "CP-1", facts, note("CP-1"))
        _finish(store, "CP-2A", (), note("CP-2A"))
        cp2g_facts = _cp2g_facts(_cp2g_case, cp2g_cites)
        _finish(store, "CP-2G", cp2g_facts, note("CP-2G"), (_cp2g_t2h7(_cp2g_case),))
    return store, pack, store.begin(MODULE)


def _head(store: Execution, module_id: str) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _finished(store: Execution, attempt: Attempt) -> Attempt:
    return next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)


def _upstream(store: Execution, attempt: Attempt) -> "cp2h.Upstream":
    return cp2h.cp2h_upstream(store=store, attempt=attempt)


def _cp1(store: Execution) -> tuple[Fact, ...]:
    return store.head_module(_head(store, "CP-1")).facts


def _bound(case: str, cp1: tuple[Fact, ...]) -> cp2h.TriggerSubmission:
    """The case's frozen payload, figures bound to the CP-1 head's ids (manifest run_time_bindings)."""
    body = stage1.bind(stage1.raw_payload(case), stage1.fig_ids(cp1))
    return cp2h.TriggerSubmission.model_validate_json(json.dumps(body))


def _submission(store: Execution, case: str = "positive") -> cp2h.TriggerSubmission:
    return _bound(case, _cp1(store))


# --- the store adapter (one adapter for submit, probe and view) ----------------------------------


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_adapter_returns_the_stage_1_input_object(case: str, tmp_path: Path) -> None:
    """Over heads settled from the oracles' own records, the adapter returns exactly the Stage 1
    test's `TriggerInputs` (scope sources in pack order, issuer name, the four reported ratios,
    the 28 CP-2G metrics), with the store's bound and current inputs in place of the stand-ins,
    and the core composes the same report."""
    store, pack, attempt = seed(tmp_path, case)
    got = cp2h._inputs(pack, _submission(store, case), _upstream(store, attempt))
    want = stage1.inputs(case)
    up = replace(want.upstream, bound=attempt.inputs, current=attempt.inputs)
    assert got == replace(want, upstream=up)
    assert [s.source_id for s in got.pack.sources] == ["identity", "financial", "ratings"]
    assert cp2h.compute(got) == cp2h.compute(replace(want, upstream=up))
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]["positive"]


def _scaled(facts: tuple[Fact, ...], metric: str, amount: str) -> tuple[Fact, ...]:
    label = f"{cp2h.LTM_COLUMN} · {metric}"
    return tuple(
        f.model_copy(update={"amount": Decimal(amount)}) if f.label == label else f for f in facts
    )


def test_adapter_follows_the_cp1_head_and_drops_what_the_core_does_not_read(
    tmp_path: Path,
) -> None:
    """A CP-1 head whose total leverage differs from the oracle, plus a decoy, at another as-of
    date: the adapter keeps the head's four ratios in its order and the T2R.4 check follows."""
    metric = cp2h.CP1_METRICS[0]
    facts = (_decoy(), *reversed(_scaled(stage1.cp1_facts("gap"), metric, "2.5")))
    store, pack, attempt = seed(tmp_path, cp1_facts=facts, as_of="2026-02-03")
    upstream = _upstream(store, attempt)
    assert upstream.cp1 == facts
    got = cp2h._inputs(pack, _submission(store), upstream)
    assert got.upstream.cp1_facts == facts[1:]
    check = next(c.fact for c in cp2h.compute(got).cells if c.fact.fact_id == "T2R.4.t01.check")
    oracle = next(
        f for f in EXPECTED["cases"]["positive"]["facts"] if f["fact_id"] == check.fact_id
    )
    assert check.text != oracle["text"]
    assert pack.run.as_of.isoformat() == "2026-02-03" and store.read().run.as_of == pack.run.as_of


@pytest.mark.parametrize("case_kind", ["synthetic", "private"])
def test_adapter_statuses_are_the_bound_input_statuses(case_kind: CaseKind, tmp_path: Path) -> None:
    """A private run with no notes settles its heads accepted, a synthetic run restricted; the
    T2R.1 upstream register states the bound statuses, never a constant."""
    synthetic = case_kind == "synthetic"
    store, pack, attempt = seed(tmp_path, case_kind=case_kind, notes=synthetic)
    want = "restricted" if synthetic else "accepted"
    upstream = _upstream(store, attempt)
    assert [i.status for i in attempt.inputs if i.input_id.startswith("CP-")] == [want] * 3
    assert (upstream.status("CP-1"), upstream.status("CP-2G"), upstream.status("CP-1D")) == (
        want,
        want,
        None,
    )
    cells = cp2h.compute(cp2h._inputs(pack, _submission(store), upstream)).cells
    statuses = {c.fact.fact_id: c.fact.text for c in cells if c.fact.table_id == "T2R.1"}
    assert statuses["T2R.1.u_cp2g.status"] == statuses["T2R.1.u_cp1.status"] == want


def test_upstream_binds_the_attempt_and_reports_the_inputs_now(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    assert upstream.bound == attempt.inputs and upstream.current == attempt.inputs
    assert upstream.inherited == ("CP-0 note", SYNTHETIC, "CP-1 note", "CP-2G note", "CP-2A note")
    snapshot = store.read()
    heads = tuple(h for h in snapshot.heads if h.module_id != "CP-2G")
    stale = _FrozenExecution(store, snapshot.model_copy(update={"heads": heads}))
    assert _upstream(stale, attempt).current == "Required upstream is unrun, stale or blocked"


def test_the_bound_cp2g_blob_is_read_not_a_later_head(tmp_path: Path) -> None:
    """The CP-2G metrics come from the blob the attempt binds: a snapshot whose CP-2G head names
    another result does not change what the attempt reads, only `current` (stale)."""
    store, _, attempt = seed(tmp_path)
    other_store, _, _ = seed(tmp_path / "other", "fixture_total_loss")
    other = _head(other_store, "CP-2G")
    blob = other_store.head_module(other).model_dump_json()
    digest = store._store(blob)
    snapshot = store.read()
    heads = tuple(
        h.model_copy(update={"result_sha256": digest}) if h.module_id == "CP-2G" else h
        for h in snapshot.heads
    )
    later = _FrozenExecution(store, snapshot.model_copy(update={"heads": heads}))
    read = _upstream(later, attempt)
    assert read.cp2g == _upstream(store, attempt).cp2g == stage1.cp2g_metrics("gap")
    assert read.cp2g != stage1.cp2g_metrics(stage1.spec("fixture_total_loss")[1])
    assert read.current != attempt.inputs


@pytest.mark.parametrize("rid,upstream_id", [("v17", "CP-2G"), ("v18", "CP-1")])
def test_a_stale_bound_upstream_is_the_oracle_issue_alone(
    rid: str, upstream_id: str, tmp_path: Path
) -> None:
    """v17/v18 (composer-only): the store-bound tuple against a current tuple in which only that
    upstream Input differs gives exactly the oracle line, before any content check."""
    store, pack, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    literal = stage1.SUBMITTED[rid]["upstream_literal"]["current"][0]
    other = Input(input_id=literal["input_id"], sha256=literal["sha256"], status=literal["status"])
    current = tuple(other if i.input_id == upstream_id else i for i in attempt.inputs)
    bound = next(i for i in attempt.inputs if i.input_id == upstream_id)
    refusal = next(r for r in EXPECTED["refusals"] if r["id"] == rid)
    tail = refusal["expected_issues"][0].split(">", 1)[1]
    want = f"{refusal['issue_prefix']}{bound.sha256[:12]}{tail}"
    stale = replace(upstream, current=current)
    sub = _submission(store)
    assert cp2h.validate_triggers(pack=pack, submission=sub, upstream=stale) == (want,)
    high = json.loads(sub.model_dump_json())
    high["views"][0]["confidence"] = "High"
    bad = cp2h.TriggerSubmission.model_validate_json(json.dumps(high))
    assert cp2h.validate_triggers(pack=pack, submission=bad, upstream=stale) == (want,)
    assert cp2h.validate_triggers(pack=pack, submission=bad, upstream=upstream) != (want,)


def test_a_bound_input_of_another_module_is_refused(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    cp1 = next(i for i in attempt.inputs if i.input_id == "CP-1")
    forged = attempt.model_copy(
        update={
            "inputs": tuple(
                i.model_copy(update={"sha256": cp1.sha256}) if i.input_id == "CP-2G" else i
                for i in attempt.inputs
            )
        }
    )
    with pytest.raises(ValueError, match="CP-2G input is a CP-1 module"):
        _upstream(store, forged)
    unbound = attempt.model_copy(
        update={"inputs": tuple(i for i in attempt.inputs if i.input_id != "CP-1")}
    )
    with pytest.raises(ValueError, match="binds no CP-1 input"):
        _upstream(store, unbound)


# --- the journal: submit, the entry validator, probe ---------------------------------------------

PAGES = frozenset({("ratings", "page:1"), ("ratings", "page:3")})


def _submit(store: Execution, attempt: Attempt, payload: str, seen: Seen | None = None) -> Any:
    read = Seen(read=PAGES) if seen is None else seen
    return cp2h.submit(store, attempt.ticket_id, STEP, payload, lambda t: cp2h.RULES(t, read))


def settled(
    root: Path, case: str = "positive", **kwargs: Any
) -> tuple[Execution, PreparedPack, Attempt, Any]:
    store, pack, attempt = seed(root, case, **kwargs)
    payload = _submission(store, case).model_dump_json()
    return store, pack, attempt, _submit(store, attempt, payload)


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_submit_settles_the_head_with_the_tail_input(case: str, tmp_path: Path) -> None:
    store, pack, attempt, submitted = settled(tmp_path, case)
    assert (submitted.nulls_resolved, submitted.prefilled, submitted.prefilled_kinds) == (
        (),
        (),
        (),
    )
    finished = _finished(store, attempt)
    assert finished.status == "finished" and finished.issues == ()
    head = _head(store, MODULE)
    assert head.status == "restricted" and head.qualification == cp2h.QUALIFICATION
    module = store.head_module(head)
    parsed = cp2h.TriggerSubmission.model_validate_json(submitted.payload)
    tail = Input(input_id="rating-triggers-submission", sha256=parsed.content_hash())
    assert module.inputs == (*attempt.inputs, tail)
    upstream = _upstream(store, attempt)
    report = cp2h.rating_triggers(pack=pack, submission=parsed, upstream=upstream)
    assert (module.facts, module.tables, module.claims) == (
        report.facts,
        report.tables,
        report.claims,
    )
    assert report.pack_sha256 == pack.content_hash()
    assert list(module.limitations) == [*EXPECTED["cases"][case]["own_limitations"], SYNTHETIC]
    assert module.inherited_limitations == tuple(
        n for n in upstream.inherited if n not in module.limitations
    )


def test_a_cited_page_not_read_is_a_journaled_invalid_step_and_the_repair_settles(
    tmp_path: Path,
) -> None:
    """t01: read_inputs only, then the valid payload: attempt 0 is invalid with the two unread
    page lines (the journaled rule); attempt 1, after both pages are read, settles."""
    t01 = next(t for t in SUBMISSIONS["tool_refusals"] if t["id"] == "t01")
    store, _, first = seed(tmp_path)
    payload = _submission(store).model_dump_json()
    _submit(store, first, payload, Seen())
    done = _finished(store, first)
    assert done.status == "finished" and list(done.issues) == t01["expected_issues"]
    assert done.steps[0].status == "invalid"
    second = store.begin(MODULE)
    assert second.number == 1 and second.repair_of == first.ticket_id
    _submit(store, second, payload)
    assert _head(store, MODULE).status == "restricted"


def test_probe_rebuilds_the_settled_head_and_writes_nothing(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot = store.read()
    cp2h.probe(store, snapshot, _finished(store, attempt))
    assert store.read() == snapshot


def test_probe_refuses_a_journal_that_does_not_rebuild(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot, finished = store.read(), _finished(store, attempt)
    step = finished.steps[0]
    other = json.loads(_submission(store).model_dump_json())
    other["overall"]["limitation"] = "A different limitation on the overall assessment."
    forged_steps = {
        "another step output": (step.model_copy(update={"output_sha256": "0" * 64}),),
        "a step that is not valid": (step.model_copy(update={"status": "invalid"}),),
        "two steps": (step, step),
        "another payload": (
            step.model_copy(update={"payload_sha256": store._store(json.dumps(other))}),
        ),
    }
    for name, steps in forged_steps.items():
        with pytest.raises(WorkflowError) as caught:
            cp2h.probe(store, snapshot, finished.model_copy(update={"steps": steps}))
        assert caught.value.code == "identity_mismatch", name


def test_probe_refuses_the_forged_first_year_in_the_result_module(tmp_path: Path) -> None:
    """A4's target (expected.tamper): T2R.6.t04.down_first lives only in the result Module."""
    store, _, attempt, _ = settled(tmp_path)
    snapshot = store.read()
    module = store.head_module(_head(store, MODULE))
    tamper = EXPECTED["tamper"]
    target = tamper["target_fact"]
    assert next(f for f in module.facts if f.fact_id == target).text == tamper["from"]
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": tamper["to"]}) if f.fact_id == target else f
                for f in module.facts
            )
        }
    )
    digest = store._store(forged.model_dump_json())
    finished = _finished(store, attempt).model_copy(update={"result_sha256": digest})
    heads = tuple(
        h.model_copy(update={"result_sha256": digest}) if h.module_id == MODULE else h
        for h in snapshot.heads
    )
    with pytest.raises(WorkflowError) as caught:
        cp2h.probe(store, snapshot.model_copy(update={"heads": heads}), finished)
    assert caught.value.code == "identity_mismatch"


def test_entry_validator_is_the_one_submit_journals_with(tmp_path: Path) -> None:
    store, pack, attempt, _ = settled(tmp_path)
    finished = _finished(store, attempt)
    outcome = cp2h.ENTRY_VALIDATOR(store, pack, finished)
    assert outcome.issues == () and outcome.retained_as(finished.steps[0])


RUN_LEVEL = [r for r in EXPECTED["refusals"] if not stage1.SUBMITTED[r["id"]].get("composer_only")]


def _refusal_text(rid: str, cp1: tuple[Fact, ...]) -> str:
    submitted = stage1.SUBMITTED[rid]
    if submitted.get("payload_text") is not None:
        return str(submitted["payload_text"])
    if submitted.get("bind_placeholders") is False:
        return json.dumps(submitted["payload"])
    return json.dumps(stage1.bind(submitted["payload"], stage1.fig_ids(cp1)))


@pytest.mark.parametrize("refusal", RUN_LEVEL, ids=lambda r: str(r["id"]))
def test_each_refusal_is_a_journaled_invalid_step_with_the_oracle_issues(
    refusal: dict[str, Any], tmp_path: Path
) -> None:
    store, _, attempt = seed(tmp_path)
    _submit(store, attempt, _refusal_text(refusal["id"], _cp1(store)))
    finished = _finished(store, attempt)
    want = list(refusal["expected_issues"])
    got = list(finished.issues)
    assert finished.status == "finished" and finished.steps[0].status == "invalid"
    if refusal["id"] == "v16":
        assert len(got) == len(want) and got[0].startswith(refusal["issue_prefix"])
    else:
        assert got == want
    assert all(len(i) <= MAX_LINE for i in got)
    rejected = store.result(finished.result_sha256 or "")
    assert rejected.status == "rejected" and list(rejected.limitations) == got
    assert not [h for h in store.read().heads if h.module_id == MODULE]


def test_two_refusals_block_the_module(tmp_path: Path) -> None:
    """expected.json cases.blocked: r01 on attempt 0 (rejected), v08 on attempt 1 (blocked)."""
    expected = EXPECTED["cases"]["blocked"]
    store, _, first = seed(tmp_path)
    _submit(store, first, _refusal_text("r01", _cp1(store)))
    assert list(_finished(store, first).issues) == expected["attempt_0"]["limitations"]
    second = store.begin(MODULE)
    assert second.number == 1 and second.repair_of == first.ticket_id
    assert list(second.repair_issues) == expected["attempt_1"]["repair_issues"]
    _submit(store, second, _refusal_text("v08", _cp1(store)))
    head = _head(store, MODULE)
    module = store.head_module(head)
    assert head.status == "blocked" and module.tables == () and module.facts == ()
    assert list(module.limitations) == expected["attempt_1"]["limitations"]
    with pytest.raises(ValueError):
        store.begin(MODULE)


def test_a_blocked_cp2g_head_refuses_the_cp2h_begin(tmp_path: Path) -> None:
    """cases.cp2g_blocked: CP-2G is a required (block) edge, so begin raises, no attempt."""
    pack = _pack("gap")
    store = Execution.create(tmp_path / "store", pack)
    _finish(store, "CP-0", tuple(_command(m) for m in ("CP-1", "CP-2A", "CP-2G", "CP-2H")), None)
    _finish(store, "CP-1", (*stage1.cp1_facts("gap"), _decoy()), None)
    _finish(store, "CP-2A", (), None)
    for _ in range(2):
        ticket = store.begin("CP-2G")
        store.finish(ticket.ticket_id, "{}", lambda _m: ("refused",))
    before = store.read()
    with pytest.raises(
        ValueError, match=EXPECTED["cases"]["cp2g_blocked"]["cp2h_begin"]["message"]
    ):
        store.begin(MODULE)
    assert store.read() == before


def test_submit_refuses_a_foreign_step(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    with pytest.raises(ValueError, match="one step"):
        cp2h.submit(store, attempt.ticket_id, "other_step", "{}", None)


def test_submit_without_rules_journals_the_validator_alone(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    cp2h.submit(store, attempt.ticket_id, STEP, _submission(store).model_dump_json(), None)
    assert _head(store, MODULE).status == "restricted"


# --- the settled head equals the oracle (A1, A2; fast form) ---------------------------------------


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_settled_facts_tables_claims_and_limitations_equal_the_oracle(
    case: str, tmp_path: Path
) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    want = EXPECTED["cases"][case]
    own = [f for f in module.facts if f.table_id.startswith("T2R.")]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    for fact, e in zip(own, want["facts"], strict=True):
        # Lineage and spelling are not stored on a Fact: both are the oracle's here, so the
        # record compares every stored field (the upstream citations here are empty).
        stage1._assert_cell(cp2h.Cell(fact, tuple(e.get("derives_from", ())), e["shown"]), e)
    names = {fid: n for n, fid in stage1.fig_ids(_cp1(store)).items()}

    def unbind(text: str) -> str:
        return stage1.REF.sub(
            lambda m: "{{FIG:" + names[m[1]] + "|" + m[2] + "}}" if m[1] in names else m[0], text
        )

    assert [
        (c.claim_id, unbind(c.text), [x.model_dump() for x in c.citations], c.limitation)
        for c in module.claims
    ] == [(c["claim_id"], c["text"], c["citations"], c["limitation"]) for c in want["claims"]]
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]
    d8 = EXPECTED["d8_table_ids"]
    tables = [t.table_id for t in module.tables]
    assert tables == [*d8["cp2h_table_ids"], *d8["module_tables_besides"]]
    assert [e["table_id"] for e in want["tables"]] == d8["cp2h_table_ids"]
    for table, e in zip(module.tables, want["tables"], strict=False):
        assert (table.table_id, table.title, [c.field for c in table.columns]) == (
            e["table_id"],
            e["title"],
            e["columns"],
        )
        assert [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] == [
            (r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]
        ]


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_reference_tables_carry_the_upstream_facts_verbatim(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    upstream = {
        f.fact_id: f
        for h in store.read().heads
        if h.module_id in ("CP-1", "CP-2G")
        for f in store.head_module(h).facts
    }
    coordinates = {"table_id", "row_id", "field"}
    want = EXPECTED["cases"][case]
    for name, label_key in (("cp1_references", "label"), ("cp2g_references", "label")):
        table = next(t for t in module.tables if t.table_id == name)
        rows = want[name]["rows"]
        assert (table.title, table.row_header) == (want[name]["title"], want[name]["row_header"])
        assert [(c.field, c.label) for c in table.columns] == [("value", "Value")]
        assert [(r.row_id, r.label) for r in table.rows] == [
            (r["row_id"], r[label_key]) for r in rows
        ]
        for row in table.rows:
            (fid,) = row.fact_ids
            copy_ = facts[fid]
            assert (copy_.table_id, copy_.row_id, copy_.field) == (name, row.row_id, "value")
            assert copy_.model_dump(exclude=coordinates) == upstream[fid].model_dump(
                exclude=coordinates
            )


def _financial_cites() -> tuple[Citation, Citation, Citation]:
    """Two quotes from one page of the frozen financial source and one from another."""
    fin = next(s for s in stage1.FINANCIAL["sources"] if s["source_id"] == "financial")

    def cite(page: int, line: int) -> Citation:
        span = fin["pages"][page]
        lines = [x for x in span["text"].split("\n") if x.strip()]
        return Citation(
            source_id="financial",
            source_sha256=fin["sha256"],
            locator=span["locator"],
            quote=lines[line],
        )

    return cite(1, 4), cite(1, 5), cite(2, 4)


def test_upstream_citations_are_appended_one_per_page_in_lineage_order(tmp_path: Path) -> None:
    """`expected.json cell_notation` and rulings stage2 round 3 item 3: after a fact's own
    (frozen) citations come the citations of the cp1/cp2g facts it derives from (directly or
    through its own facts), one per (source, page) not yet cited: the first quote on that page in
    derives_from order. CP-2G facts here carry two quotes of one page, so the first-quote and the
    last-quote mutants both give another tuple."""
    a, b, c = _financial_cites()
    cites = {
        "T2H.6.a25.total_leverage": (a, b),
        "T2H.6.d26.net_leverage": (c, b),
        "T2H.6.d27.net_leverage": (a,),
        "T2H.6.d28.net_leverage": (b, c),
    }
    store, _, _, _ = settled(tmp_path, cp2g_cites=cites)
    module = store.head_module(_head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    want = {e["fact_id"]: e for e in EXPECTED["cases"]["positive"]["facts"]}

    def own(fid: str) -> tuple[Citation, ...]:
        return tuple(Citation.model_validate(x) for x in want[fid].get("citations", ()))

    assert facts["T2R.4.t01.actual"].citations == (a,)
    assert facts["T2R.4.t01.headroom"].citations == (*own("T2R.4.t01.headroom"), a)
    assert facts["T2R.6.t04.down_first"].citations == (*own("T2R.6.t04.down_first"), c, b)
    assert facts["T2R.4.t01.check"].citations == (a,)  # the CP-1 ratio carries none
    untouched = [f for f in module.facts if f.table_id == "T2R.2"]
    assert untouched and all(f.citations == own(f.fact_id) for f in untouched)
    assert facts["T2H.6.a25.total_leverage"].citations == (a, b)  # the reference copy, verbatim


def _pages(citations: Any) -> list[tuple[str, str]]:
    return [(c["source_id"], c["locator"]) for c in citations]


def test_oracle_derived_facts_cite_one_quote_per_page() -> None:
    """Round 5 item 17 at the close release: every derived fact of every oracle case carries one
    citation per (source, page); the quote is the first input quote on that page."""
    seen = 0
    for name, case in EXPECTED["cases"].items():
        for f in case.get("facts", ()):
            if f.get("derives_from") and f.get("citations"):
                pages = _pages(f["citations"])
                assert len(pages) == len(set(pages)), (name, f["fact_id"])
                seen += 1
    assert seen


def test_a_derived_fact_cites_the_first_input_quote_on_each_page(tmp_path: Path) -> None:
    """The settled module meets the same rule, and keeps the first of the inputs' quotes (so the
    last-quote mutant fails): `T2R.9.total.triggers` derives from several rows of one page."""
    store, _, _, _ = settled(tmp_path)
    module = store.head_module(_head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    want = {e["fact_id"]: e for e in EXPECTED["cases"]["positive"]["facts"]}
    derived = [fid for fid, e in want.items() if e.get("derives_from") and e.get("citations")]
    assert derived
    for fid in derived:
        pages = [(c.source_id, c.locator) for c in facts[fid].citations]
        assert len(pages) == len(set(pages)), fid
        assert [c.model_dump() for c in facts[fid].citations[: len(want[fid]["citations"])]] == (
            want[fid]["citations"]
        ), fid


@pytest.mark.parametrize("case", ("positive", "gap"))
def test_view_equals_the_committed_view_tree(case: str, tmp_path: Path) -> None:
    """`cases/cp2h-owner/cp2h-view-tree.json`: the keys and shape of the body `view` serves."""
    store, _, attempt = seed(tmp_path, case)
    view_tree.check("cp2h", case, cp2h.view(_FrozenExecution(store, store.read()), attempt)[1])


# --- the shared hostile set and model text (rulings stage2 Q5; round 3 item 2) -----------------


def test_shared_hostile_text_set_over_the_schemas() -> None:
    """Rulings stage2 Q5: the schema refuses the hostile set only with `ValueError`."""
    for schema in cp2h.SCHEMAS.values():
        assert_hostile_refused(schema)


# No free-text path of the schema is stored verbatim: every hostile value is an issue
# (`model_text_failures` runs with an empty verbatim set at run level, `test_owner_cp2h.py`).
CP2H_VERBATIM: frozenset[tuple[str | int, ...]] = frozenset()


def test_model_text_is_refused_at_the_validator() -> None:
    """Round 3 item 2 at the validator: a hostile value on any free-text path of the positive
    payload (24 paths) is an issue, so nothing raises after the binding write."""
    base = stage1.inputs("positive")
    payload = json.loads(base.submission.model_dump_json())
    paths = free_text_paths(payload, cp2h.TriggerSubmission)
    assert any(path_matches(("views", "*", "rationale"), p) for p in paths)
    assert any(path_matches(("gaps", "*", "action"), p) for p in paths)
    for path in paths:
        for value in MODEL_TEXT_HOSTILE:
            text = json.dumps(with_text(payload, path, value))
            issues = cp2h.payload_issues(text, pack=base.pack, upstream=base.upstream)
            assert issues and all(len(i) <= MAX_LINE for i in issues), (path, value)


# --- the exact `read_inputs` view -----------------------------------------------------------------

FORBIDDEN_KEYS = {"quote", "citations", "record_json"}
TREE_KEYS = list(MANIFEST["tool_use"]["view_tree_draft"]["keys"])


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _rows(case: str, table_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = next(
        t for t in EXPECTED["cases"][case]["tables"] if t["table_id"] == table_id
    )["rows"]
    return rows


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_view_is_the_lease_key_tree_without_quotes(case: str, tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path, case)
    digest, body = cp2h.view(_FrozenExecution(store, store.read()), attempt)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    tree = json.loads(body)
    assert body == json.dumps(tree, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert list(tree) == TREE_KEYS and not _keys(tree) & FORBIDDEN_KEYS
    quotes = [c["quote"] for v in stage1.raw_payload(case)["views"] for c in v["evidence"]]
    assert quotes and not [q for q in quotes if q in body]
    e = EXPECTED["cases"][case]
    facts = {f["fact_id"]: f for f in e["facts"]}
    assert tree["upstream"] == [
        {"module_id": m, "status": "restricted"}
        for m in EXPECTED["execution"]["inputs"]["positive"][1:]
    ]
    register = tree["register"]
    pages = [p["locator"] for p in stage1._variant(e["source_variant"])["pages"]]
    assert (register["state"], register["source_id"], register["pages"]) == (
        "present",
        "ratings",
        pages,
    )
    assert [a["row"] for a in register["agencies"]] == [r["row_id"] for r in _rows(case, "T2R.2")]
    for agency in register["agencies"]:
        for field in ("agency", "rating", "outlook"):
            assert agency[field] == facts[f"T2R.2.{agency['row']}.{field}"]["text"], field
    assert [t["row"] for t in tree["triggers"]] == [r["row_id"] for r in _rows(case, "T2R.3")]
    for trigger in tree["triggers"]:
        row = trigger["row"]
        for field in ("agency", "direction", "metric", "comparison"):
            assert trigger[field] == facts[f"T2R.3.{row}.{field}"]["text"], field
        threshold = facts[f"T2R.3.{row}.threshold"]
        known = threshold["status"] == "known"
        assert trigger["threshold"] == {
            "ref": threshold["fact_id"] if known else None,
            "shown": threshold["shown"] if known else None,
            "status": threshold["status"],
        }
    refs = {r["fact_id"]: r for r in e["cp2g_references"]["rows"]}
    assert tree["cp2g"]["status"] == "restricted"
    assert [r["row"] for r in tree["cp2g"]["rows"]] == list(cp2h.CP2G_ROWS)
    cells = [(r["row"], f, c) for r in tree["cp2g"]["rows"] for f, c in r["metrics"].items()]
    metrics = stage1.cp2g_metrics(e["cp2g_head"]["case"])
    assert [c["ref"] for _, _, c in cells] == [f.fact_id for f in metrics.facts]
    assert set(e["cp2g_head"]["facts_read"]) == set(refs)
    for row, field, cell in cells:
        fact = metrics.fact(row, field)
        assert (cell["status"], cell["limitation"]) == (fact.status, fact.limitation)
        if cell["ref"] in refs:
            assert cell["shown"] == refs[cell["ref"]]["shown"], cell["ref"]
    by_metric = cp2h.select_cp1(_cp1(store))
    shown = {f["ref"]: f["shown"] for f in tree["cp1_facts"]}
    assert set(shown) <= {f.fact_id for f in by_metric.values()} and "decoy-revenue" not in shown
    for figure in e["figures"].values():
        assert shown[by_metric[figure["cp1_metric"]].fact_id] == figure["spelled"]
    assert tree["inherited_limitations"] == list(_upstream(store, attempt).inherited)


def test_view_of_an_absent_or_unparseable_agency_source(tmp_path: Path) -> None:
    """No ratings source: the register is absent and no trigger is offered; a source the parse
    rule refuses (register_not_found): present, with nothing parsed. CP-2G stays as read."""
    store, pack, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    full = cp2h.context_block(pack=pack, upstream=upstream)
    kept = tuple(s for s in pack.sources if s.source_id != "ratings")
    absent = cp2h.context_block(pack=pack.model_copy(update={"sources": kept}), upstream=upstream)
    assert absent["register"] == {"state": "absent", "source_id": None, "pages": [], "agencies": []}
    assert absent["triggers"] == [] and absent["cp2g"] == full["cp2g"]
    broken: dict[str, Any] = cp2h.context_block(
        pack=_pack(variant="register_not_found"), upstream=upstream
    )
    assert (broken["register"]["state"], broken["register"]["agencies"]) == ("present", [])
    assert broken["triggers"] == [] and broken["cp2g"] == full["cp2g"]


def test_view_is_the_registered_view_of_the_step(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    frozen = _FrozenExecution(store, store.read())
    assert owner._VIEWS[STEP](frozen, attempt) == cp2h.view(frozen, attempt)


def test_the_view_follows_the_heads(tmp_path: Path) -> None:
    metric = cp2h.CP1_METRICS[0]
    facts = (*_scaled(stage1.cp1_facts("gap"), metric, "2.5"), _decoy())
    store, _, attempt = seed(tmp_path, "fixture_total_loss", cp1_facts=facts)
    tree = json.loads(cp2h.view(store, attempt)[1])
    total = cp2h.select_cp1(facts)[metric]
    assert next(f for f in tree["cp1_facts"] if f["ref"] == total.fact_id)["shown"] == "2.50x"
    loss = {
        r["fact_id"]: r for r in EXPECTED["cases"]["fixture_total_loss"]["cp2g_references"]["rows"]
    }
    gap = {r["fact_id"]: r for r in EXPECTED["cases"]["positive"]["cp2g_references"]["rows"]}
    cells = {c["ref"]: c for r in tree["cp2g"]["rows"] for c in r["metrics"].values()}
    moved = [fid for fid in loss if loss[fid]["shown"] != gap[fid]["shown"]]
    assert moved and all(cells[fid]["shown"] == loss[fid]["shown"] for fid in moved)


# --- registrations (lease Files; append-only rows) -----------------------------------------------


def test_registrations_equal_the_lease() -> None:
    expected = owner.OwnerSpec(
        module_id=MODULE,
        steps=(
            owner.StepSpec(
                step_id=STEP,
                schema=cp2h.TriggerSubmission,
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
    assert owner._CORES[MODULE] is cp2h
    assert owner._QUALIFICATION[MODULE] is cp2h.QUALIFICATION
    assert owner._PROBES[MODULE] is cp2h.probe
    assert owner._VIEWS[STEP] is cp2h.view
    assert owner._ENTRY_VALIDATORS[MODULE] is cp2h.ENTRY_VALIDATOR
    assert MODULE not in owner._PRECHECKS
    owner._check_steps(MODULE, owner.OWNER_SPECS[MODULE])


def test_registrations_are_appended_after_their_dependencies() -> None:
    """Append-only: the shipped prefix stands, and each CP-2H row comes after the rows of the
    owners it consumes (CP-1, CP-2G). Later appends are not this test's."""
    assert tuple(owner.OWNER_SPECS)[:5] == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._QUALIFICATION)[:4] == ("CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._PROBES)[:4] == ("CP-0", "CP-1", "CP-1A", "CP-2")
    assert tuple(owner._VIEWS)[:1] == ("credit_synthesis",)
    assert tuple(owner._ENTRY_VALIDATORS)[:2] == ("CP-1A", "CP-2")
    assert tuple(owner._CORES)[:2] == ("CP-DR", "CP-3D")
    for table, key, after in (
        (owner.OWNER_SPECS, MODULE, ("CP-1", "CP-2G")),
        (owner._CORES, MODULE, ("CP-2G",)),
        (owner._QUALIFICATION, MODULE, ("CP-1", "CP-2G")),
        (owner._PROBES, MODULE, ("CP-1", "CP-2G")),
        (owner._ENTRY_VALIDATORS, MODULE, ("CP-2G",)),
        (owner._VIEWS, STEP, ("forward_credit_model",)),
    ):
        order = list(table)
        assert all(order.index(key) > order.index(a) for a in after), (key, after)


def test_a_plan_with_cp2h_passes_check_specs(tmp_path: Path) -> None:
    for case in ("positive", "gap"):
        planned = owner._check_specs(_pack(case), owner.OWNER_SPECS, None, tmp_path / case)
        assert list(planned) == EXPECTED["execution"]["plan_order"][case]


# --- bindings and the _Spec row (lease D7) --------------------------------------------------------

BLOCK = "rating-triggers"


def test_the_block_is_already_in_the_preset_once() -> None:
    blocks = next(b for pid, _, _, b in _PRESETS if pid == "distressed_restructuring")
    assert blocks.count(BLOCK) == 1
    assert not [
        b
        for pid, _, _, bs in _PRESETS
        if pid != "distressed_restructuring"
        for b in bs
        if b == BLOCK
    ]


def test_spec_row_is_in_the_cp2a_composition() -> None:
    fp05 = EXPECTED["cases"]["positive"]["FP05"]["blocks"][BLOCK]
    spec = _spec_of(BLOCK)
    assert _DISTRESSED[BLOCK] is spec
    assert (spec.title, spec.owner, spec.kind, spec.producers, spec.route_label) == (
        fp05["title"],
        fp05["owner"],
        fp05["kind"],
        (MODULE,),
        "Full analysis",
    )
    keys = list(_DISTRESSED)
    assert keys[:2] == ["downside-stress", "break-points"]


def test_shipped_maps_hold_cp2h_once_after_its_producers() -> None:
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.count(MODULE) == 1
    assert ids.index(MODULE) > max(ids.index("CP-1"), ids.index("CP-2G"))


def _module_view(pack: PreparedPack, module: Module) -> View:
    return View(
        run=pack.run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Rating triggers",
                aliases=(),
                status=module.status,
                artifact_sha256=module.content_hash(),
                facts=module.facts,
                tables=module.tables,
                claims=module.claims,
                limitations=module.limitations,
            ),
        ),
    )


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_bindings_place_every_expected_table_exactly_once(case: str, tmp_path: Path) -> None:
    store, pack, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    cp2h_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    assert validate_bindings(_module_view(pack, module), (cp2h_map,)) == ()
    by_table = {e.fact_coord.table_id: e for e in cp2h_map.entries}
    assert len(by_table) == len(cp2h_map.entries)
    fp05 = EXPECTED["cases"][case]["FP05"]
    for block_id, block in fp05["blocks"].items():
        for tab in block["tabs"]:
            entry = by_table[tab["table_id"]]
            assert (entry.block_id, entry.label) == (block_id, tab["label"])
    for table in fp05["evidence_rail_tables"]:
        assert by_table[table].block_id == "evidence"
    for table in fp05["limitations_rail_tables"]:
        assert by_table[table].block_id == "limitations"
    placed = {t["table_id"] for b in fp05["blocks"].values() for t in b["tabs"]}
    rails = {*fp05["evidence_rail_tables"], *fp05["limitations_rail_tables"]}
    assert set(by_table) == placed | rails == {t.table_id for t in module.tables}
    assert all(e.cell_slot.startswith("cp2h-") for e in cp2h_map.entries)


@pytest.mark.parametrize("case", stage1.COMPOSED)
def test_fp05_cells_are_the_settled_spellings(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    tables = {t.table_id: t for t in module.tables}
    for block in EXPECTED["cases"][case]["FP05"]["blocks"].values():
        for tab in block["tabs"]:
            table = tables[tab["table_id"]]
            assert [r.row_id for r in table.rows] == [r["row_id"] for r in tab["rows"]]
            for row, want in zip(table.rows, tab["rows"], strict=True):
                assert row.label == want["label"]
                assert list(row.fact_ids) == [c["fact_id"] for c in want["cells"]]
                for fid, cell in zip(row.fact_ids, want["cells"], strict=True):
                    _uc, state, text = fact_spelling(facts[fid], "G1")
                    assert (state, text.replace("G1", "G#")) == (cell["state"], cell["shown"])


# --- D3: CP-2H consumes the genuine CP-2G head (expected.json execution.consumption) -------------


def test_d3_cp2h_consumes_the_genuine_cp2g_head(tmp_path: Path) -> None:
    """(a)-(d) over a CP-2G head the real CP-2G core settled on its frozen gap literal: the
    attempt binds the final heads hash for hash, the CP-2G head is the bound Input, the lineage
    reads the T2H.6 facts (5 actuals, 30 yearly headrooms, 10 first years) and every settled
    value and copy is the CP-2G head's own; its citations ride along at run time."""
    store, pack, attempt, _ = settled(tmp_path, genuine=True)
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    finished = _finished(store, attempt)
    # (a)
    assert [i.input_id for i in finished.inputs] == EXPECTED["execution"]["inputs"]["positive"]
    assert finished.inputs[0].sha256 == snapshot.pack_sha256
    assert all(i.sha256 == heads[i.input_id].result_sha256 for i in finished.inputs[1:])
    # (b)
    cp2g_head = heads["CP-2G"]
    bound = next(i for i in finished.inputs if i.input_id == "CP-2G")
    assert bound.sha256 == cp2g_head.result_sha256 and cp2g_head.qualification == cp2g.QUALIFICATION
    # (c)
    result = cp2h.compute(cp2h._inputs(pack, _submission(store), _upstream(store, finished)))
    lineage = {c.fact.fact_id: c.derives_from for c in result.cells}
    want = EXPECTED["cases"]["positive"]["facts"]
    assert lineage == {f["fact_id"]: tuple(f.get("derives_from", ())) for f in want}

    def reads(fid: str, prefix: str) -> list[str]:
        return [r.removeprefix("cp2g:") for r in lineage[fid] if r.startswith("cp2g:" + prefix)]

    actual = [f for f in lineage if f.startswith("T2R.4.") and f.endswith(".actual")]
    yearly = [
        f for f in lineage if f.startswith("T2R.5.") and f.rsplit(".", 1)[1] in ("y1", "y2", "y3")
    ]
    first = [f for f in lineage if f.startswith("T2R.6.") and len(reads(f, "T2H.6.")) == 3]
    assert [len(reads(f, "T2H.6.a25.")) for f in actual] == [1] * 5
    assert len(yearly) == 30 and all(len(reads(f, "T2H.6.")) == 1 for f in yearly)
    assert len(first) == 10
    # (d)
    module = store.head_module(heads[MODULE])
    head_facts = {f.fact_id: f for f in store.head_module(cp2g_head).facts}
    facts = {f.fact_id: f for f in module.facts}
    for fid in actual:
        (ref,) = reads(fid, "T2H.6.a25.")
        src = head_facts[ref]
        assert (facts[fid].status, facts[fid].amount) == (src.status, src.amount), fid
        per_page = {(c.source_id, c.locator): c for c in reversed(src.citations)}
        assert facts[fid].citations == tuple(c for c in src.citations if c in per_page.values())
    assert any(head_facts[r].citations for f in actual for r in reads(f, "T2H.6.a25."))
    coordinates = {"table_id", "row_id", "field"}
    table = next(t for t in module.tables if t.table_id == "cp2g_references")
    copied = [row.fact_ids[0] for row in table.rows]
    assert sorted(copied) == EXPECTED["cases"]["positive"]["cp2g_head"]["facts_read"]
    for fid in copied:
        assert facts[fid].model_dump(exclude=coordinates) == head_facts[fid].model_dump(
            exclude=coordinates
        )
    for fact, e in zip(
        (f for f in module.facts if f.table_id.startswith("T2R.")), want, strict=True
    ):
        own = [Citation.model_validate(x) for x in e.get("citations", ())]
        assert list(fact.citations[: len(own)]) == own, fact.fact_id
        bare = cp2h.Cell(
            fact.model_copy(update={"citations": tuple(own)}), lineage[fact.fact_id], e["shown"]
        )
        stage1._assert_cell(bare, e)


# --- round 4: the T2R.10 gap fields are run text; the id is free text ---------------------------

_GAP_FIELDS = ("gap", "why_it_matters", "affected_analysis", "action")


def _gap_facts() -> tuple[Fact, ...]:
    payload = _payload()
    for name in _GAP_FIELDS:
        payload["gaps"][0][name] = f"Headroom of {{T2R.4.t01.headroom|x}} is in {name}."
    rep = cp2h.compute(stage1.inputs("positive", payload))
    facts = [c.fact for c in rep.cells]
    facts += [cp2h._moved(r.fact, cp2h.CP1_REFERENCES[0], r.row_id) for r in rep.cp1_references]
    return tuple(facts)


def _gap_page(facts: tuple[Fact, ...]) -> dict[str, dict[str, Any]]:
    module = ModuleView(
        module_id="CP-2H",
        title="CP-2H",
        aliases=(),
        status="restricted",
        artifact_sha256="c" * 64,
        facts=facts,
        limitations=(),
    )
    base = _what_changed_view("positive")
    return _payload_facts(base.model_copy(update={"modules": (module,)}))


@pytest.mark.parametrize("name", _GAP_FIELDS)
def test_t2r10_gap_run_text_shows_the_figure_not_the_reference(name: str) -> None:
    shown = _gap_page(_gap_facts())[f"T2R.10.g01.{name}"]
    for key in ("display", "table_display"):
        assert "{T2R.4.t01.headroom|x}" not in shown[key]
        assert "1.08x" in shown[key]


def test_t2r10_free_id_with_brackets_is_shown_as_written() -> None:
    sic = "CP-2H-GAP-001 [sic]"
    facts = tuple(
        f.model_copy(update={"text": sic}) if f.fact_id == "T2R.10.g01.id" else f
        for f in _gap_facts()
    )
    assert _gap_page(facts)["T2R.10.g01.id"]["display"] == sic
