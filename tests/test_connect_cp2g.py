"""CP-2G Stage 2: the connection of the Stage 1 core to the store, the registrations, the
bindings, the readers and the fast consumption proof (`docs/CP2G-OWNER-LEASE.md`,
`docs/G1X-OWNER-CORE-PROTOCOL.md`).

Expectations come from the lease and `cases/cp2g-owner/{expected,submissions}.json` (with the
pinned CP-2A and CP-1D oracles), never from the code under test. The stores here are real
`Execution` stores whose CP-0, CP-1, CP-1D and CP-2A heads are settled through `begin`/`finish`
from the oracles' own records (CP-2A also through the real CP-2A core), so no CP-1 promotion
runs: the genuine runs are `tests/test_owner_cp2g.py` and `tests/cp2g_runs.py`. The fixtures vary
the CP-1 amounts, the as-of date, the case kind (heads settle accepted or restricted), the CP-1D
state, the CP-2A head, and the CP-1D supported facts (`test_the_forecast_follows_the_cp1d_facts`
settles a CP-1D head whose three facts differ from the oracle's), so a constant equal to the
oracle cannot pass.
"""

import hashlib
import importlib
import json
import re
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pytest
import test_method_cp2a as cp2a_stage1
import test_method_cp2g as stage1
from defect_classes import (
    MODEL_TEXT_HOSTILE,
    assert_hostile_refused,
    free_text_paths,
    path_matches,
    with_text,
)

from deploy_vii import prose
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, Input, Module, ModuleView, Run, View
from deploy_vii.execution import Attempt, Execution, Head, Qualification
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import _DISTRESSED, _PRESETS, _spec_of, fact_spelling
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.owners import cp2a, cp2g
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
fw: Any = importlib.import_module("test_financial_workflow")

MODULE = "CP-2G"
STEP = "forward_credit_model"
SYNTHETIC = "Synthetic case; not real issuer qualification"
MAX_LINE = 600
EXPECTED = stage1.EXPECTED
SUBMISSIONS = stage1.SUBMISSIONS
MANIFEST = stage1.MANIFEST
LTM = cp2g.LTM_PERIOD
Q3 = "Q3 25: 2025-07-01 to 2025-09-30"
CaseKind = Literal["public", "private", "synthetic"]
# Stage 2 round 5 item 10: the free-text paths of the positive payload whose value is stored as
# plain text and never built as `RunText`: each driver, downside and assessment `limitation`
# is `Claim.limitation` of its T2H.3 claim (sink: `forward_model` claims). Every other
# free-text path (rationales, gap texts) must be refused.
CP2G_VERBATIM: frozenset[tuple[str | int, ...]] = frozenset(
    {
        ("base_drivers", "revenue_growth", "limitation"),
        ("base_drivers", "ebitda_margin", "limitation"),
        ("base_drivers", "dividends", "limitation"),
        ("downside", "limitation"),
        ("assessment", "limitation"),
    }
)


def _payload(case: str = "positive") -> dict[str, Any]:
    bound: dict[str, Any] = stage1._bind_all(stage1._payload(case))
    return bound


def _submission(case: str = "positive") -> cp2g.ForwardSubmission:
    return cp2g.ForwardSubmission.model_validate_json(json.dumps(_payload(case)))


def _with(context: cp2g.ForwardContext, payload: dict[str, Any]) -> cp2g.ForwardInputs:
    sub = cp2g.ForwardSubmission.model_validate_json(json.dumps(payload))
    return cp2g.ForwardInputs(context=context, submission=sub)


# --- backlog (stage2-backlog.md CP-2G rows; protocol section 6) ----------------------------------


def _shock(row: str, field: str, period: str | None) -> Fact:
    known = period is not None
    return Fact(
        fact_id=f"T2B.1.{row}.{field}",
        label=field,
        table_id="T2B.1",
        row_id=row,
        field=field,
        amount=Decimal("0.2") if known else None,
        status="known" if known else "missing",
        unit="PERCENT",
        period=period,
        limitation=None if known else "Not stated",
    )


def _text(fact_id: str, value: str) -> Fact:
    head, row, field = fact_id.rsplit(".", 2)
    return Fact(fact_id=fact_id, label=field, table_id=head, row_id=row, field=field, text=value)


def _cp2a_module(periods: dict[str, tuple[str | None, str | None]]) -> Module:
    facts: list[Fact] = []
    for row, (decline, increase) in periods.items():
        facts += [
            _text(f"T2B.1.{row}.name", f"Scenario {row}"),
            _shock(row, "ebitda_decline", decline),
            _shock(row, "interest_increase", increase),
        ]
    return Module(
        run_id="r",
        issuer_id="i",
        as_of=date(2026, 1, 10),
        module_id="CP-2A",
        status="restricted",
        facts=tuple(facts),
        limitations=("note",),
    )


def test_cp2a_base_period_is_the_one_period_of_the_t2b1_shocks() -> None:
    """Round 13 R1 L2, backlog item: the CP-2A base period is the one period the T2B.1 shocks
    share, read from the head, never a constant."""
    for period in (LTM, Q3):
        head = cp2g.cp2a_of(_cp2a_module({"s01": (period, period), "s02": (period, period)}))
        assert head.base_period == period
        assert [s.name for s in head.scenarios] == ["Scenario s01", "Scenario s02"]


@pytest.mark.parametrize("periods", [{"s01": (LTM, Q3)}, {"s01": (LTM, LTM), "s02": (Q3, Q3)}])
def test_cp2a_t2b1_facts_that_differ_in_period_raise_the_invariant(
    periods: dict[str, tuple[str | None, str | None]],
) -> None:
    with pytest.raises(ValueError) as caught:
        cp2g.cp2a_of(_cp2a_module(periods))
    assert str(caught.value) == "CP-2G: CP-2A T2B.1 facts differ in period"


def test_an_unsettled_shock_without_a_period_is_not_a_period_conflict() -> None:
    """Stage 2 round 5 item 5 (read for CP-2G): a shock with no period does not differ."""
    head = cp2g.cp2a_of(_cp2a_module({"s01": (LTM, None), "s02": (LTM, LTM)}))
    assert head.base_period == LTM
    assert head.scenarios[0].increase.status == "missing"
    with pytest.raises(ValueError) as caught:
        cp2g.cp2a_of(_cp2a_module({"s01": (None, None)}))
    assert str(caught.value) == "CP-2G: CP-2A T2B.1 facts state no period"


def test_scenario_name_is_the_settled_t2b1_name_fact() -> None:
    module = _cp2a_module({"s01": (LTM, LTM)})
    renamed = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": "Renamed downturn"})
                if f.fact_id == "T2B.1.s01.name"
                else f
                for f in module.facts
            )
        }
    )
    assert cp2g.cp2a_of(renamed).scenarios[0].name == "Renamed downturn"
    missing = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.field != "name")}
    )
    with pytest.raises(ValueError, match=r"has no fact T2B\.1\.s01\.name"):
        cp2g.cp2a_of(missing)


def test_prose_issue_quoting_the_payload_is_clipped() -> None:
    """Protocol section 6, 0d-c audit (cp2g `_text_issues`): a `prose.issues` line quotes the
    analyst's text, so it is cut at 600 characters before the journal sees it."""
    payload = _payload()
    payload["assessment"]["rationale"] = "A figure of " + "7" * 5000 + " appears."
    issues = cp2g.content_issues(_with(stage1._context("positive"), payload))
    assert [i for i in issues if i.startswith("assessment.rationale: ")]
    assert all(len(i) <= MAX_LINE for i in issues), [len(i) for i in issues]


def test_the_join_of_a_raised_composition_is_bounded() -> None:
    """`compute` raises on any issue; its message is the bounded list (20 lines and a count)."""
    payload = _payload()
    blank = {"gap": " ", "why_it_matters": " ", "affected_analysis": " ", "action": " "}
    payload["gaps"] = [dict(payload["gaps"][0], **blank) for _ in range(8)]
    inputs = _with(stage1._context("positive"), payload)
    assert len(cp2g.content_issues(inputs)) == 32
    with pytest.raises(ValueError) as caught:
        cp2g.compute(inputs)
    assert str(caught.value).endswith("; 12 further issues not listed")  # 20 shown of 32


def test_stale_text_is_clipped() -> None:
    (issue,) = cp2g.stale_issues(bound=(), current="Required upstream " + "x" * 5000)
    assert issue.startswith("Stale inputs: Required upstream") and len(issue) <= MAX_LINE


def test_claim_text_is_checked_with_the_type_the_claim_builds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage 2 round 3 item 2: a rationale becomes `Claim.text` (`RunText`); if `prose.issues`
    ever passed text `RunText` refuses, the validator still journals the type's own message
    (`include_input=False`) instead of the composition raising after the binding write."""
    monkeypatch.setattr(prose, "issues", lambda text, bound, names=(): [])
    payload = _payload()
    payload["downside"]["rationale"] = "{low"
    issues = cp2g.content_issues(_with(stage1._context("positive"), payload))
    assert issues == (
        "downside.rationale: Value error, Malformed run text: unbalanced or empty reference",
    )


def test_payload_text_is_parsed_through_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protocol section 6 (the cp2g `payload_issues` rewire): the schema validates the bounded
    `json_object` document, never raw text; text it refuses keeps the frozen shape issue (r14)."""
    seen: list[str] = []
    real = cp2g.ForwardSubmission.model_validate_json

    def spy(text: str | bytes, **kwargs: Any) -> cp2g.ForwardSubmission:
        seen.append(str(text))
        return real(text, **kwargs)

    monkeypatch.setattr(cp2g.ForwardSubmission, "model_validate_json", spy)
    spaced = json.dumps(_payload(), indent=2)
    assert cp2g.payload_issues(spaced, stage1._context("positive")) == ()
    assert seen and spaced not in seen
    r14 = stage1._refusal_text("r14")
    assert list(cp2g.payload_issues(r14, stage1._context("positive"))) == (
        stage1._expected_issues("r14")
    )
    for hostile in ('{"a": "\\ud800"}', "[" * 5000 + "]" * 5000, '{"x": NaN}'):
        issues = cp2g.payload_issues(hostile, stage1._context("positive"))
        assert issues and all(len(i) <= MAX_LINE for i in issues)


def test_shared_hostile_text_set_over_the_schemas() -> None:
    """Rulings stage2 Q5: the schema refuses the hostile set only with `ValueError`."""
    for schema in cp2g.SCHEMAS.values():
        assert_hostile_refused(schema)


def test_model_text_is_refused_or_stored_verbatim() -> None:
    """Round 3 item 2 and round 5 item 10 at the validator (the run-level form, with the wedge
    check, is `test_owner_cp2g.py`): every hostile value on every free-text path is an issue,
    except on the `CP2G_VERBATIM` paths, where it composes and is stored as a claim limitation."""
    payload = _payload()
    paths = free_text_paths(payload, cp2g.ForwardSubmission)
    assert all(any(path_matches(p, path) for path in paths) for p in CP2G_VERBATIM)
    context = stage1._context("positive")
    for path in paths:
        for value in MODEL_TEXT_HOSTILE:
            text = json.dumps(with_text(payload, path, value))
            issues = cp2g.payload_issues(text, context)
            if any(path_matches(p, path) for p in CP2G_VERBATIM):
                assert issues == (), (path, value)
                result = cp2g.compute(_with(context, json.loads(text)))
                assert value in [c.limitation for c in result.claims], (path, value)
            else:
                assert issues, (path, value)


# --- the plug-in parts that need no store (protocol section 2) ---------------------------------


def test_core_attributes_match_the_lease() -> None:
    assert (cp2g.MODULE_ID, cp2g.STEP_ID, cp2g.SCHEMA_VERSION) == (
        MODULE,
        STEP,
        "forward-credit-model/1",
    )
    assert cp2g.QUALIFICATION == Qualification(implementation="implemented")
    assert cp2g.STEP_IDS == (STEP,)
    assert dict(cp2g.SCHEMAS) == {STEP: cp2g.ForwardSubmission}
    assert cp2g.SUBMISSION_INPUT == "forward-credit-model-submission"
    for name in ("probe", "view", "submit", "ENTRY_VALIDATOR", "cp2g_reader", "cp2a_reader"):
        assert callable(getattr(cp2g, name)), name
    for name in ("cp1d_reader", "cp2g_upstream", "context_block", "cp2g_module"):
        assert callable(getattr(cp2g, name)), name
    for name in ("validate_forward", "forward_model"):
        assert callable(getattr(cp2g, name)), name
    # Rule mode `none`, no precheck (lease Files): nothing to register for either.
    assert not hasattr(cp2g, "RULES") and not hasattr(cp2g, "precheck")


@pytest.mark.parametrize("case", stage1.RUNS)
def test_schemas_round_trip_and_give_the_tail_digest(case: str) -> None:
    parsed = cp2g.SCHEMAS[STEP].model_validate_json(json.dumps(_payload(case)))
    assert cp2g.SCHEMAS[STEP].model_validate_json(parsed.model_dump_json()) == parsed
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()


# --- a real store, heads settled from the oracles' own records ----------------------------------


def _run(case: str, *, as_of: str | None, case_kind: CaseKind) -> Run:
    document = dict(MANIFEST["cases"][case]["run"])
    document["case_kind"] = case_kind
    if as_of is not None:
        document["as_of"] = as_of
    return Run.model_validate_json(json.dumps(document))


def _pack(
    case: str = "positive", *, as_of: str | None = None, case_kind: CaseKind = "synthetic"
) -> PreparedPack:
    base: PreparedPack = fw.make_pack()
    return PreparedPack(run=_run(case, as_of=as_of, case_kind=case_kind), sources=base.sources)


def _command(module_id: str) -> Fact:
    return Fact(
        fact_id=f"t8-{module_id.lower()}",
        label="Command",
        table_id="T8",
        row_id=module_id,
        field="exact_command",
        text=f"Run {module_id}",
    )


def _finish(store: Execution, module_id: str, facts: tuple[Fact, ...], note: str | None) -> None:
    ticket = store.begin(module_id)
    run = store.read().run
    module = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=module_id,
        inputs=ticket.inputs,
        facts=facts,
        limitations=() if note is None else (note,),
    )
    store.finish(ticket.ticket_id, module.model_dump_json(), lambda _m: ())


def _blocked(store: Execution, module_id: str) -> None:
    """Two refused settlements: attempt 0 rejected, the repair blocked."""
    for _ in range(2):
        ticket = store.begin(module_id)
        store.finish(ticket.ticket_id, "{}", lambda _m: ("refused",))


def oracle_facts(source: dict[str, Any], case: str) -> tuple[Fact, ...]:
    return tuple(stage1._fact(rec) for rec in source["cases"][case]["facts"])


def _cp2a_genuine(store: Execution, facts: tuple[Fact, ...]) -> None:
    """The real CP-2A core over the seeded CP-1 head: the frozen CP-2A positive literal (the
    copy in `submissions.json upstream_step_literals`), figures bound by the CP-2A rule."""
    ticket = store.begin("CP-2A")
    literal = SUBMISSIONS["upstream_step_literals"]["CP-2A"]["downside_pathway"]
    payload = cp2a_stage1.bind_payload(literal, cp2a_stage1.fig_ids(facts))
    done = cp2a.submit(store, ticket.ticket_id, "downside_pathway", json.dumps(payload), None)
    assert done.journal.status == "finished" and done.journal.issues == ()


def seed(
    root: Path,
    case: str = "positive",
    *,
    cp1d_blocked: bool = False,
    cp2a_source: str = "positive",
    genuine_cp2a: bool = False,
    cp1_facts: tuple[Fact, ...] | None = None,
    cp1d_facts: tuple[Fact, ...] | None = None,
    as_of: str | None = None,
    case_kind: CaseKind = "synthetic",
    notes: bool = True,
) -> tuple[Execution, PreparedPack, Attempt]:
    """A real store with CP-0, CP-1, CP-1D (when requested) and CP-2A settled, CP-2G begun.
    `cp1d_facts` replaces the CP-1D oracle facts the CP-1D head settles with."""
    pack = _pack(case, as_of=as_of, case_kind=case_kind)
    store = Execution.create(root / "store", pack)

    def note(module_id: str) -> str | None:
        return f"{module_id} note" if notes else None

    commands = tuple(_command(m) for m in ("CP-1", "CP-1D", "CP-2A", "CP-2G"))
    _finish(store, "CP-0", commands, note("CP-0"))
    facts = stage1._cp1_facts(case) if cp1_facts is None else cp1_facts
    _finish(store, "CP-1", facts, note("CP-1"))
    if cp1d_blocked:
        _blocked(store, "CP-1D")
    elif "CP-1D" in pack.run.requested_modules:
        body = oracle_facts(stage1.CP1D_EXP, "positive") if cp1d_facts is None else cp1d_facts
        _finish(store, "CP-1D", body, note("CP-1D"))
    if genuine_cp2a:
        _cp2a_genuine(store, facts)
    else:
        _finish(store, "CP-2A", oracle_facts(stage1.CP2A_EXP, cp2a_source), note("CP-2A"))
    return store, pack, store.begin(MODULE)


def _case_seed(root: Path, case: str, **kwargs: Any) -> tuple[Execution, PreparedPack, Attempt]:
    return seed(root, case, cp1d_blocked=case == "cp1d_blocked", **kwargs)


def _head(store: Execution, module_id: str) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _finished(store: Execution, attempt: Attempt) -> Attempt:
    return next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)


def _upstream(store: Execution, attempt: Attempt) -> "cp2g.Upstream":
    return cp2g.cp2g_upstream(store=store, attempt=attempt)


# --- the store adapter (one adapter for submit, probe and view) ----------------------------------


@pytest.mark.parametrize("case", stage1.RUNS)
def test_adapter_returns_the_stage_1_input_object(case: str, tmp_path: Path) -> None:
    """Over heads settled from the oracle's own records, the adapter returns exactly the Stage 1
    test's `ForwardInputs` (CP-1 facts, CP-2A head, CP-1D head, statuses, names), and the core
    composes the same result."""
    store, pack, attempt = _case_seed(tmp_path, case)
    got = cp2g._inputs(pack, _submission(case), _upstream(store, attempt))
    assert got == stage1._inputs(case)
    assert cp2g.compute(got) == stage1._result(case)


def test_adapter_reads_the_frozen_cp2a_gap_head(tmp_path: Path) -> None:
    """fixture_cp2a_gap_head: the CP-2A gap head (base period Q3 25) read from the store."""
    store, pack, attempt = seed(tmp_path, cp2a_source="gap")
    case = "fixture_cp2a_gap_head"
    got = cp2g._inputs(pack, _submission(case), _upstream(store, attempt))
    want = stage1._inputs(case)
    assert got.context.cp2a == want.context.cp2a and got.context.cp2a.base_period == Q3
    same = replace(got, context=replace(got.context, cp1d=want.context.cp1d))
    assert cp2g.compute(same) == stage1._result(case)


def _scaled(facts: tuple[Fact, ...], metric: str, amount: str) -> tuple[Fact, ...]:
    label = f"{cp2g.LTM_COLUMN} · {metric}"
    return tuple(
        f.model_copy(update={"amount": Decimal(amount)}) if f.label == label else f for f in facts
    )


def _decoy() -> Fact:
    return Fact(
        fact_id="decoy-net-debt",
        label=f"{cp2g.LTM_COLUMN} · net_debt",
        table_id="T4.10",
        row_id="net_debt",
        amount=Decimal(1),
        unit="MILLIONS",
        currency="USD",
        scale=Decimal(1000000),
        period=LTM,
        calculation_id="calc:decoy",
    )


def test_adapter_follows_the_cp1_head_and_drops_what_the_core_does_not_read(
    tmp_path: Path,
) -> None:
    facts = (*_scaled(stage1._cp1_facts("positive"), "revenue", "150"), _decoy())
    store, pack, attempt = seed(tmp_path, cp1_facts=facts, as_of="2026-02-03")
    upstream = _upstream(store, attempt)
    assert upstream.cp1 == facts
    got = cp2g._inputs(pack, _submission(), upstream)
    assert got.context.cp1_facts == facts[:-1]
    revenue = next(c.fact for c in cp2g.compute(got).cells if c.fact.fact_id == "T2H.4.a25.revenue")
    assert revenue.amount == Decimal(150)
    assert pack.run.as_of.isoformat() == "2026-02-03"


@pytest.mark.parametrize("case_kind", ["synthetic", "private"])
def test_adapter_statuses_are_the_bound_input_statuses(case_kind: CaseKind, tmp_path: Path) -> None:
    """A private run with no notes settles its heads accepted, a synthetic run restricted; the
    adapter passes the bound statuses through, never a constant."""
    synthetic = case_kind == "synthetic"
    store, pack, attempt = seed(tmp_path, case_kind=case_kind, notes=synthetic)
    want = "restricted" if synthetic else "accepted"
    ctx = cp2g._inputs(pack, _submission(), _upstream(store, attempt)).context
    assert (ctx.cp1_status, ctx.cp2a_status, ctx.cp1d.status) == (want, want, want)
    assert [i.status for i in attempt.inputs if i.input_id.startswith("CP-")] == [want] * 4


def test_adapter_reads_each_status_from_its_own_bound_input(tmp_path: Path) -> None:
    """CP-1 and CP-2A bound under different statuses, and a bound CP-2D (an optional edge this
    version never reads): each context status is that input's own."""
    store, pack, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    cp2d = Input(input_id="CP-2D", sha256="d" * 64, status="blocked")
    bound = tuple(
        i.model_copy(update={"status": "accepted"}) if i.input_id == "CP-1" else i
        for i in upstream.bound
    )
    ctx = cp2g._inputs(pack, _submission(), replace(upstream, bound=(*bound, cp2d))).context
    assert (ctx.cp1_status, ctx.cp2a_status, ctx.cp2d_status) == (
        "accepted",
        "restricted",
        "blocked",
    )
    assert cp2g._inputs(pack, _submission(), upstream).context.cp2d_status is None


def test_upstream_binds_the_attempt_and_reports_the_inputs_now(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    assert upstream.bound == attempt.inputs and upstream.current == attempt.inputs
    assert upstream.inherited == ("CP-0 note", SYNTHETIC, "CP-1 note", "CP-1D note", "CP-2A note")
    snapshot = store.read()
    heads = tuple(h for h in snapshot.heads if h.module_id != "CP-2A")
    stale = _FrozenExecution(store, snapshot.model_copy(update={"heads": heads}))
    assert _upstream(stale, attempt).current == "Required upstream is unrun, stale or blocked"


@pytest.mark.parametrize("rid,upstream_id", [("v18", "CP-2A"), ("v19", "CP-1D"), ("v20", "CP-1")])
def test_a_stale_bound_upstream_is_the_oracle_issue_alone(
    rid: str, upstream_id: str, tmp_path: Path
) -> None:
    """v18-v20 (ruling 10): the store-bound tuple against a current tuple in which only that one
    upstream Input differs gives exactly the oracle line, and no content check runs."""
    store, pack, attempt = seed(tmp_path)
    upstream = _upstream(store, attempt)
    literal = stage1.REFUSALS[rid]["upstream_literal"]["current"][0]
    other = Input(input_id=literal["input_id"], sha256=literal["sha256"], status=literal["status"])
    current = tuple(other if i.input_id == upstream_id else i for i in attempt.inputs)
    bound = next(i for i in attempt.inputs if i.input_id == upstream_id)
    (issue,) = stage1._expected_issues(rid)
    want = re.sub(r"<12 hex of [^>]*>", bound.sha256[:12], issue)
    stale = replace(upstream, current=current)
    assert cp2g.validate_forward(pack=pack, submission=_submission(), upstream=stale) == (want,)
    high = _payload()
    high["assessment"]["confidence"] = "High"
    bad = cp2g.ForwardSubmission.model_validate_json(json.dumps(high))
    assert cp2g.validate_forward(pack=pack, submission=bad, upstream=stale) == (want,)
    assert cp2g.validate_forward(pack=pack, submission=bad, upstream=upstream) == (cp2g.HIGH_ISSUE,)


def test_a_refused_current_inputs_text_is_one_clipped_stale_issue(tmp_path: Path) -> None:
    store, pack, attempt = seed(tmp_path)
    upstream = replace(_upstream(store, attempt), current="Required upstream " + "x" * 5000)
    (issue,) = cp2g.validate_forward(pack=pack, submission=_submission(), upstream=upstream)
    assert issue.startswith("Stale inputs: Required upstream") and len(issue) <= MAX_LINE


def test_a_bound_input_of_another_module_is_refused(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    cp1 = next(i for i in attempt.inputs if i.input_id == "CP-1")
    forged = attempt.model_copy(
        update={
            "inputs": tuple(
                i.model_copy(update={"sha256": cp1.sha256}) if i.input_id == "CP-2A" else i
                for i in attempt.inputs
            )
        }
    )
    with pytest.raises(ValueError, match="CP-2A input is a CP-1 module"):
        _upstream(store, forged)


# --- the journal: submit, the entry validator, probe ---------------------------------------------


def _submit(store: Execution, attempt: Attempt, payload: str) -> Any:
    return cp2g.submit(store, attempt.ticket_id, STEP, payload, None)


def settled(
    root: Path, case: str = "positive", **kwargs: Any
) -> tuple[Execution, PreparedPack, Attempt, Any]:
    store, pack, attempt = _case_seed(root, case, **kwargs)
    return store, pack, attempt, _submit(store, attempt, json.dumps(_payload(case)))


@pytest.mark.parametrize("case", stage1.RUNS)
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
    assert head.status == EXPECTED["cases"][case]["module_status"] == "restricted"
    assert head.qualification == cp2g.QUALIFICATION
    module = store.head_module(head)
    parsed = cp2g.ForwardSubmission.model_validate_json(submitted.payload)
    tail = Input(input_id="forward-credit-model-submission", sha256=parsed.content_hash())
    assert module.inputs == (*attempt.inputs, tail)
    upstream = _upstream(store, attempt)
    report = cp2g.forward_model(pack=pack, submission=parsed, upstream=upstream)
    assert (module.facts, module.tables, module.claims) == (
        report.facts,
        report.tables,
        report.claims,
    )
    assert list(module.limitations) == [*EXPECTED["cases"][case]["own_limitations"], SYNTHETIC]
    assert module.inherited_limitations == tuple(
        n for n in upstream.inherited if n not in module.limitations
    )


def test_probe_rebuilds_the_settled_head_and_writes_nothing(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot = store.read()
    cp2g.probe(store, snapshot, _finished(store, attempt))
    assert store.read() == snapshot


def test_probe_refuses_a_journal_that_does_not_rebuild(tmp_path: Path) -> None:
    store, _, attempt, _ = settled(tmp_path)
    snapshot, finished = store.read(), _finished(store, attempt)
    step = finished.steps[0]
    other = _payload()
    other["assessment"]["rationale"] = "A different, figure-free rationale for the assessment."
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
            cp2g.probe(store, snapshot, finished.model_copy(update={"steps": steps}))
        assert caught.value.code == "identity_mismatch", name


def test_probe_refuses_a_forged_first_year_in_the_result_module(tmp_path: Path) -> None:
    """A4's target (expected.tamper): the T2H.7.b03.down_first text lives only in the result
    Module, so a head whose Module says otherwise does not rebuild."""
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
        cp2g.probe(store, snapshot.model_copy(update={"heads": heads}), finished)
    assert caught.value.code == "identity_mismatch"


def test_entry_validator_is_the_one_submit_journals_with(tmp_path: Path) -> None:
    store, pack, attempt, _ = settled(tmp_path)
    finished = _finished(store, attempt)
    outcome = cp2g.ENTRY_VALIDATOR(store, pack, finished)
    assert outcome.issues == () and outcome.retained_as(finished.steps[0])


RUN_LEVEL = [rid for rid in stage1.REFUSALS if rid not in ("v18", "v19", "v20")]


@pytest.mark.parametrize("rid", RUN_LEVEL)
def test_each_refusal_is_a_journaled_invalid_step_with_the_oracle_issues(
    rid: str, tmp_path: Path
) -> None:
    store, _, attempt = seed(tmp_path)
    _submit(store, attempt, stage1._refusal_text(rid))
    finished = _finished(store, attempt)
    want = stage1._expected_issues(rid)
    assert finished.status == "finished" and list(finished.issues) == want
    assert finished.steps[0].status == "invalid"
    assert all(len(i) <= MAX_LINE for i in finished.issues)
    rejected = store.result(finished.result_sha256 or "")
    assert rejected.status == "rejected" and list(rejected.limitations) == want
    assert not [h for h in store.read().heads if h.module_id == MODULE]


@pytest.mark.parametrize("case", ["positive", "blocked"])
def test_two_refusals_block_the_module(case: str, tmp_path: Path) -> None:
    """expected.json cases.blocked: r01 on attempt 0 (rejected), v13 on attempt 1 (blocked).

    Release item (frozen oracle): the `blocked` run requests CP-2G alone, so CP-1D is unbound and
    v13's assessment rationale (the positive text, which names the CP-1D supported leverage) is
    also an unresolved reference there; `attempt_1.limitations` lists only the High line, which
    holds on a run that binds CP-1D (the positive pack) and is asserted on that one."""
    expected = EXPECTED["cases"]["blocked"]
    store, _, first = seed(tmp_path, case, cp1_facts=stage1._cp1_facts("gap"))
    _submit(store, first, stage1._refusal_text("r01"))
    assert list(_finished(store, first).issues) == expected["attempt_0"]["limitations"]
    second = store.begin(MODULE)
    assert second.number == 1 and second.repair_of == first.ticket_id
    assert list(second.repair_issues) == expected["attempt_1"]["repair_issues"]
    _submit(store, second, stage1._refusal_text("v13"))
    head = _head(store, MODULE)
    module = store.head_module(head)
    assert head.status == "blocked" and module.tables == () and module.facts == ()
    unresolved = "assessment.rationale: Unresolved reference: T1D.6.supported.total_leverage"
    oracle = expected["attempt_1"]["limitations"]
    assert list(module.limitations) == (oracle if case == "positive" else [unresolved, *oracle])
    read = cp2g.cp2g_reader(store, head)
    assert (read.status, read.head_sha256, read.facts, read.limitations) == (
        "blocked",
        head.result_sha256,
        (),
        (),
    )


def test_submit_refuses_rules_and_a_foreign_step(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    payload = json.dumps(_payload())
    with pytest.raises(ValueError, match="rule mode none"):
        cp2g.submit(store, attempt.ticket_id, STEP, payload, lambda text: ())
    with pytest.raises(ValueError, match="one step"):
        cp2g.submit(store, attempt.ticket_id, "other_step", payload, None)


# --- the settled head equals the oracle (A1, A2, cp1d_blocked; fast form) ------------------------


@pytest.mark.parametrize("case", stage1.RUNS)
def test_settled_facts_claims_and_limitations_equal_the_oracle(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    want = EXPECTED["cases"][case]
    own = [f for f in module.facts if f.table_id.startswith("T2H.")]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    for fact, e in zip(own, want["facts"], strict=True):
        # A settled Fact stores no lineage and no spelling: both are the oracle's own here, so
        # the record compares every stored field (lineage is the D3 test's, spelling FP05's).
        cell = cp2g.Cell(fact, tuple(e.get("derives_from", ())), e["shown"])
        assert stage1._record(cell) == e, fact.fact_id
    assert [(c.claim_id, c.text, c.citations, c.limitation) for c in module.claims] == [
        (c["claim_id"], stage1._bind(c["text"]), (), c["limitation"]) for c in want["claims"]
    ]
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]
    tables = [t.table_id for t in module.tables]
    assert tables == [*cp2g.TABLES, "cp1_references", "cp2a_references", "cp1d_references"]
    for table, e in zip(module.tables, want["tables"], strict=False):
        assert (table.table_id, table.title) == (e["table_id"], e["title"])
        assert [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] == [
            (r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]
        ]


@pytest.mark.parametrize("case", stage1.RUNS)
def test_reference_tables_carry_the_upstream_facts_verbatim(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    facts = {f.fact_id: f for f in module.facts}
    upstream = {
        f.fact_id: f
        for h in store.read().heads
        if h.module_id in ("CP-1", "CP-1D", "CP-2A")
        for f in store.head_module(h).facts
    }
    coordinates = {"table_id", "row_id", "field"}
    for name in ("cp1_references", "cp2a_references", "cp1d_references"):
        table = next(t for t in module.tables if t.table_id == name)
        want = EXPECTED["cases"][case][name]
        assert (table.title, table.row_header) == (want["title"], want["row_header"])
        assert [(c.field, c.label) for c in table.columns] == [("value", "Value")]
        assert [(r.row_id, r.label) for r in table.rows] == [
            (r["row_id"], r["label"]) for r in want["rows"]
        ]
        for row in table.rows:
            (fid,) = row.fact_ids
            copy = facts[fid]
            assert (copy.table_id, copy.row_id, copy.field) == (name, row.row_id, "value")
            assert copy.model_dump(exclude=coordinates) == upstream[fid].model_dump(
                exclude=coordinates
            )
    cp1d = next(t for t in module.tables if t.table_id == "cp1d_references")
    assert cp1d.limitation == EXPECTED["cases"][case]["cp1d_references"].get("note")


# --- the exact `read_inputs` view -----------------------------------------------------------------

FORBIDDEN_KEYS = {"quote", "citations", "record_json"}
TREE_KEYS = list(MANIFEST["tool_use"]["view_tree_draft"]["keys"])


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _quotes(store: Execution) -> set[str]:
    return {
        c.quote for h in store.read().heads for f in store.head_module(h).facts for c in f.citations
    }


@pytest.mark.parametrize("case", stage1.RUNS)
def test_view_is_the_lease_key_tree_without_quotes(case: str, tmp_path: Path) -> None:
    store, _, attempt = _case_seed(tmp_path, case)
    digest, body = cp2g.view(_FrozenExecution(store, store.read()), attempt)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    tree = json.loads(body)
    assert body == json.dumps(tree, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    assert list(tree) == TREE_KEYS and not _keys(tree) & FORBIDDEN_KEYS
    assert _quotes(store) and not [q for q in _quotes(store) if q in body]
    e = EXPECTED["cases"][case]
    assert [u["module_id"] for u in tree["upstream"]] == [
        i for i in EXPECTED["execution"]["inputs"]["gap" if case == "gap" else "positive"][1:]
    ]
    base = tree["base"]
    assert (base["period"], base["forecast_periods"]) == (e["base_period"], e["forecast_years"])
    assert set(base["operands"]) == set(cp2g.OPERAND_METRIC.values())
    assert len(base["operands"]) + len(base["ratios"]) == len(cp2g.CP1_METRICS)
    revenue = next(f for f in stage1._cp1_facts(case) if f.row_id == "revenue")
    spelled = e["figures"]["revenue_ltm"]["spelled"]
    assert base["operands"]["revenue"] == {
        "ref": revenue.fact_id,
        "shown": spelled,
        "status": "known",
        "limitation": None,
    }
    figures = {f["ref"]: f for f in tree["cp1_facts"]}
    assert figures[revenue.fact_id]["shown"] == spelled
    assert [d["name"] for d in tree["drivers"]] == [*cp2g.DRIVERS, "minimum_liquidity"]
    assert tree["drivers"][0]["bounds"] == {"min": "-1", "max": "1", "places": 4}
    assert tree["drivers"][-1]["may_be_not_assessed"] is True
    head = stage1._cp2a_head("positive")
    assert tree["cp2a"]["base_period"] == head.base_period
    assert [(s["row"], s["name"]) for s in tree["cp2a"]["scenarios"]] == [
        (s.row, s.name) for s in head.scenarios
    ]
    assert [b["row"] for b in tree["cp2a"]["breaks"]] == [b.row for b in head.breaks]
    s03 = next(s for s in tree["cp2a"]["scenarios"] if s["row"] == "s03")
    ref01 = e["cp2a_references"]["rows"][0]
    assert s03["ebitda_decline"] == {"shown": ref01["shown"], "status": "known"}
    assert tree["cp1d"]["state"] == e["cp1d_head"]["state"]
    assert tree["break_metrics_offered"] == ["total_leverage", "net_leverage", "interest_coverage"]
    assert tree["inherited_limitations"] == list(_upstream(store, attempt).inherited)
    bound = tree["cp1d"]["state"] == "bound"
    assert [f["ref"] for f in tree["cp1d_facts"]] == (list(cp2g.CP1D_IDS) if bound else [])
    assert (tree["cp1d"]["supported_ebitda"] is not None) == bound


def test_view_is_the_registered_view_of_the_step(tmp_path: Path) -> None:
    store, _, attempt = seed(tmp_path)
    frozen = _FrozenExecution(store, store.read())
    assert owner._VIEWS[STEP](frozen, attempt) == cp2g.view(frozen, attempt)


def test_the_view_follows_the_heads(tmp_path: Path) -> None:
    facts = _scaled(stage1._cp1_facts("positive"), "revenue", "150")
    store, _, attempt = seed(tmp_path, cp1_facts=facts, cp2a_source="gap")
    tree = json.loads(cp2g.view(store, attempt)[1])
    assert tree["base"]["operands"]["revenue"]["shown"] == "150 US$ m"
    assert tree["cp2a"]["base_period"] == Q3


# --- registrations (lease Files; append-only rows) -----------------------------------------------


def test_registrations_equal_the_lease() -> None:
    expected = owner.OwnerSpec(
        module_id=MODULE,
        steps=(
            owner.StepSpec(
                step_id=STEP,
                schema=cp2g.ForwardSubmission,
                sources=False,
                extract=False,
                upstream_grant=None,
                inputs="module_context",
                rules="none",
            ),
        ),
        entry="owner_core",
        kind="analytical",
        publish=None,
    )
    assert owner.OWNER_SPECS[MODULE] == expected
    assert MODULE in owner.SUPPORTED_ANALYTICAL
    assert owner._CORES[MODULE] is cp2g
    assert owner._QUALIFICATION[MODULE] is cp2g.QUALIFICATION
    assert owner._PROBES[MODULE] is cp2g.probe
    assert owner._VIEWS[STEP] is cp2g.view
    assert owner._ENTRY_VALIDATORS[MODULE] is cp2g.ENTRY_VALIDATOR
    assert MODULE not in owner._PRECHECKS
    owner._check_steps(MODULE, owner.OWNER_SPECS[MODULE])


def test_registrations_are_appended_after_their_dependencies() -> None:
    """Append-only: the shipped prefix stands, and each CP-2G row comes after the rows of the
    owners it consumes (CP-2A, CP-1D). Later appends are not this test's."""
    assert tuple(owner.OWNER_SPECS)[:5] == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._QUALIFICATION)[:4] == ("CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._PROBES)[:4] == ("CP-0", "CP-1", "CP-1A", "CP-2")
    assert tuple(owner._VIEWS)[:1] == ("credit_synthesis",)
    assert tuple(owner._ENTRY_VALIDATORS)[:2] == ("CP-1A", "CP-2")
    assert tuple(owner._CORES)[:2] == ("CP-DR", "CP-3D")
    for table, key, after in (
        (owner.OWNER_SPECS, MODULE, ("CP-2A", "CP-1D")),
        (owner._CORES, MODULE, ("CP-2A", "CP-1D")),
        (owner._QUALIFICATION, MODULE, ("CP-2A", "CP-1D")),
        (owner._PROBES, MODULE, ("CP-2A", "CP-1D")),
        (owner._ENTRY_VALIDATORS, MODULE, ("CP-2A", "CP-1D")),
        (owner._VIEWS, STEP, ("downside_pathway", "earnings_quality")),
    ):
        order = list(table)
        assert all(order.index(key) > order.index(a) for a in after), (key, after)


def test_a_plan_with_cp2g_passes_check_specs(tmp_path: Path) -> None:
    for case in ("positive", "gap"):
        planned = owner._check_specs(_pack(case), owner.OWNER_SPECS, None, tmp_path / case)
        assert list(planned) == EXPECTED["execution"]["plan_order"][case]


# --- bindings and the _Spec rows (lease D7) -------------------------------------------------------

BLOCKS = ("forward-credit-path", "forward-breakpoints")


def test_preset_inserts_the_two_blocks_after_the_cp2a_pair() -> None:
    blocks = next(b for pid, _, _, b in _PRESETS if pid == "distressed_restructuring")
    pair = blocks.index("downside-stress")
    assert blocks[pair : pair + 4] == ("downside-stress", "break-points", *BLOCKS)
    assert blocks[:1] == ("distress-gate",) and len(set(blocks)) == len(blocks)
    others = [b for pid, _, _, bs in _PRESETS if pid != "distressed_restructuring" for b in bs]
    assert not set(BLOCKS) & set(others)


def test_spec_rows_are_in_the_cp2a_composition() -> None:
    fp05 = EXPECTED["cases"]["positive"]["FP05"]["blocks"]
    for block in BLOCKS:
        spec = _spec_of(block)
        assert _DISTRESSED[block] is spec
        assert (spec.title, spec.owner, spec.kind, spec.producers, spec.route_label) == (
            fp05[block]["title"],
            fp05[block]["owner"],
            fp05[block]["kind"],
            (MODULE,),
            "Full analysis",
        )
    keys = list(_DISTRESSED)
    assert keys[:2] == ["downside-stress", "break-points"]


def test_shipped_maps_hold_cp2g_once_after_its_producers() -> None:
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.count(MODULE) == 1
    assert ids.index(MODULE) > max(ids.index("CP-2A"), ids.index("CP-1D"))


@pytest.mark.parametrize("case", stage1.RUNS)
def test_bindings_place_every_expected_table_exactly_once(case: str, tmp_path: Path) -> None:
    store, pack, _, _ = settled(tmp_path, case)
    module = store.head_module(_head(store, MODULE))
    view = View(
        run=pack.run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Forward credit model",
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
    cp2g_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    assert validate_bindings(view, (cp2g_map,)) == ()
    by_table = {e.fact_coord.table_id: e for e in cp2g_map.entries}
    assert len(by_table) == len(cp2g_map.entries)
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
    assert set(by_table) == placed | rails
    assert all(e.cell_slot.startswith("cp2g-") for e in cp2g_map.entries)


@pytest.mark.parametrize("case", stage1.RUNS)
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


# --- the reader the lease pins for CP-2H and CP-4C (Public API, Consumption) -------------------

FORECAST_ROWS = ("b26", "b27", "b28", "d26", "d27", "d28")


def _pinned(break_rows: list[str]) -> list[str]:
    return [
        *(f"T2H.4.{r}.{f}" for r in ("a25", *FORECAST_ROWS) for f in ("revenue", "ebitda", "fcf")),
        *(
            f"T2H.5.{r}.{f}"
            for r in FORECAST_ROWS
            for f in ("interest", "closing_debt", "closing_cash", "accessible_liquidity")
        ),
        *(
            f"T2H.6.{r}.{f}"
            for r in ("a25", *FORECAST_ROWS)
            for f in ("total_leverage", "net_leverage", "interest_coverage", "fcf_to_debt")
        ),
        *(f"T2H.7.{r}.{c}_first" for r in break_rows for c in ("base", "down")),
        *(
            f"T2H.8.{c}.{f}"
            for c in ("base", "down")
            for f in (
                "trajectory",
                "total_leverage_fy28",
                "change_vs_fy25",
                "peak_total_leverage",
                "peak_period",
            )
        ),
        "T2H.3.d01.source",
        "T2H.3.d02.source",
    ]


@pytest.mark.parametrize("case", stage1.RUNS)
def test_reader_exposes_what_the_lease_pins(case: str, tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path, case)
    head = _head(store, MODULE)
    module = store.head_module(head)
    facts = {f.fact_id: f for f in module.facts}
    read = cp2g.cp2g_reader(store, head)
    assert (read.status, read.head_sha256) == ("restricted", head.result_sha256)
    assert read.limitations == module.limitations and read.limitations[-1] == SYNTHETIC
    breaks = [*EXPECTED["cases"][case]["cp2a_head"]["break_rows"], "m01"]
    assert read.break_rows == tuple(breaks)
    assert [f.fact_id for f in read.facts] == _pinned(breaks)
    assert all(f == facts[f.fact_id] for f in read.facts)
    s = EXPECTED["cases"][case]["cp2a_head"]["downside_scenario"]
    assert read.fact("T2H.3.d01.source").text == f"CP-2A T2B.1.{s}.ebitda_decline"
    assert read.fact("T2H.3.d02.source").text == f"CP-2A T2B.1.{s}.interest_increase"
    tamper = EXPECTED["tamper"]
    if case == "positive":
        assert read.fact(tamper["target_fact"]).text == tamper["from"]
    with pytest.raises(ValueError, match="not exposed"):
        read.fact("T2H.1.u_cp1.module")


def test_reader_follows_the_head_not_the_oracle(tmp_path: Path) -> None:
    facts = _scaled(stage1._cp1_facts("positive"), "revenue", "150")
    store, _, _, _ = settled(tmp_path, cp1_facts=facts)
    read = cp2g.cp2g_reader(store, _head(store, MODULE))
    assert read.fact("T2H.4.a25.revenue").amount == Decimal(150)


def test_reader_refuses_another_module_and_a_stale_head(tmp_path: Path) -> None:
    store, _, _, _ = settled(tmp_path)
    with pytest.raises(ValueError, match="not a CP-2G head"):
        cp2g.cp2g_reader(store, _head(store, "CP-2A"))
    stale = _head(store, MODULE).model_copy(update={"status": "stale"})
    with pytest.raises(ValueError, match="CP-2G head is stale"):
        cp2g.cp2g_reader(store, stale)


def test_consumer_readers_read_the_cp2a_and_cp1d_heads(tmp_path: Path) -> None:
    store, _, _ = seed(tmp_path / "blocked", "cp1d_blocked", cp1d_blocked=True)
    assert cp2g.cp1d_reader(store, _head(store, "CP-1D")) == cp2g.Cp1dHead(status="blocked")
    assert cp2g.cp2a_reader(store, _head(store, "CP-2A")) == stage1._cp2a_head("positive")
    other, _, _ = seed(tmp_path / "bound")
    assert cp2g.cp1d_reader(other, _head(other, "CP-1D")) == stage1._cp1d_head("positive")
    with pytest.raises(ValueError, match="not a CP-2A head"):
        cp2g.cp2a_reader(other, _head(other, "CP-1D"))
    with pytest.raises(ValueError, match="not a CP-1D head"):
        cp2g.cp1d_reader(other, _head(other, "CP-2A"))


# --- consumption (D3): CP-2G reads the settled CP-2A and CP-1D heads ---------------------------


def test_the_forecast_follows_the_cp1d_facts(tmp_path: Path) -> None:
    """D3 strength: a CP-1D head whose supported EBITDA and leverages differ from the oracle's
    (40.0, 2.5, 1.25; the oracle has 31.8, 1.57, 0.94) moves T2H.2.*_supported and
    T2H.8.*.ebitda_fy26_vs_supported with it, so CP-2G cannot take them from a constant while
    only the CP-1D status is bound."""
    moved = {
        "T1D.3.supported.value": Decimal("40.0"),
        "T1D.6.supported.total_leverage": Decimal("2.5"),
        "T1D.6.supported.net_leverage": Decimal("1.25"),
    }
    oracle = oracle_facts(stage1.CP1D_EXP, "positive")
    seeded = tuple(
        f.model_copy(update={"amount": moved[f.fact_id]}) if f.fact_id in moved else f
        for f in oracle
    )
    assert {f.fact_id: f.amount for f in seeded if f.fact_id in moved} == moved
    assert all(f.amount != moved[f.fact_id] for f in oracle if f.fact_id in moved)
    store, _, _, _ = settled(tmp_path, cp1d_facts=seeded)
    mine = {f.fact_id: f for f in store.head_module(_head(store, MODULE)).facts}
    assert mine["T2H.2.ebitda_supported.value"].amount == Decimal("40.0")
    assert mine["T2H.2.total_leverage_supported.value"].amount == Decimal("2.5")
    assert mine["T2H.2.net_leverage_supported.value"].amount == Decimal("1.25")
    reader = cp2g.cp1d_reader(store, _head(store, "CP-1D"))
    assert reader.supported is not None and reader.supported.amount == Decimal("40.0")
    for case, row in (("base", "b26"), ("down", "d26")):
        ebitda = mine[f"T2H.4.{row}.ebitda"].amount
        assert ebitda is not None
        delta = mine[f"T2H.8.{case}.ebitda_fy26_vs_supported"].amount
        assert delta == ebitda - Decimal("40.0"), case


def test_d3_cp2g_consumes_the_genuine_cp2a_head_and_the_cp1d_head(tmp_path: Path) -> None:
    """A6 (lease Consumption proof) over a store whose CP-2A head the real CP-2A core settled:
    (a) the attempt binds the final heads hash for hash in plan order; (b) each head's hash is
    the bound Input; (c) the copied cells equal the heads' own facts, the T2H.3 source texts
    name the CP-2A row, the reference tables carry the heads' facts verbatim, and the composer's
    lineage lists the CP-2A and CP-1D facts it read (6, 20 and 6 facts)."""
    store, pack, attempt = seed(tmp_path, genuine_cp2a=True)
    _submit(store, attempt, json.dumps(_payload()))
    heads = {h.module_id: h for h in store.read().heads}
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]["positive"]
    for item in attempt.inputs[1:]:
        head = heads[item.input_id]
        assert (item.sha256, item.status) == (head.result_sha256, head.status)
    module = store.head_module(heads[MODULE])
    mine = {f.fact_id: f for f in module.facts}
    theirs = {
        m: {f.fact_id: f for f in store.head_module(heads[m]).facts} for m in ("CP-2A", "CP-1D")
    }
    cp2a_facts, cp1d_facts = theirs["CP-2A"], theirs["CP-1D"]
    s = EXPECTED["cases"]["positive"]["cp2a_head"]["downside_scenario"]
    for n in (1, 2, 3):
        assert mine[f"T2H.3.d01.fy{n}"].amount == cp2a_facts[f"T2B.1.{s}.ebitda_decline"].amount
        assert mine[f"T2H.3.d02.fy{n}"].amount == cp2a_facts[f"T2B.1.{s}.interest_increase"].amount
    assert mine["T2H.3.d01.source"].text == f"CP-2A T2B.1.{s}.ebitda_decline"
    assert mine["T2H.3.d02.source"].text == f"CP-2A T2B.1.{s}.interest_increase"
    rows = EXPECTED["cases"]["positive"]["cp2a_head"]["break_rows"]
    for row in rows:
        for field, source in (("level", "level"), ("static_decline", "required_decline")):
            copy, origin = mine[f"T2H.7.{row}.{field}"], cp2a_facts[f"T2B.6.{row}.{source}"]
            assert (copy.status, copy.amount) == (origin.status, origin.amount), row
    supported = mine["T2H.2.ebitda_supported.value"].amount
    assert supported == cp1d_facts["T1D.3.supported.value"].amount
    coordinates = {"table_id", "row_id", "field"}
    for name, source_facts in (("cp2a_references", cp2a_facts), ("cp1d_references", cp1d_facts)):
        table = next(t for t in module.tables if t.table_id == name)
        assert table.rows
        for ref in table.rows:
            (fid,) = ref.fact_ids
            assert mine[fid].model_dump(exclude=coordinates) == source_facts[fid].model_dump(
                exclude=coordinates
            )
    parsed = cp2g.ForwardSubmission.model_validate_json(json.dumps(_payload()))
    cells = cp2g.compute(cp2g._inputs(pack, parsed, _upstream(store, attempt))).cells
    lineage = {c.fact.fact_id: c.derives_from for c in cells}
    shocks = {
        **{f"T2H.4.d2{n}.ebitda": f"cp2a:T2B.1.{s}.ebitda_decline" for n in (6, 7, 8)},
        **{f"T2H.5.d2{n}.interest": f"cp2a:T2B.1.{s}.interest_increase" for n in (6, 7, 8)},
    }
    assert all(source in lineage[fid] for fid, source in shocks.items())
    breaks = [
        fid
        for row in rows
        for fid in (
            f"T2H.7.{row}.{f}" for f in ("level", "static_decline", "base_first", "down_first")
        )
        if any(d.startswith(f"cp2a:T2B.6.{row}.") for d in lineage[fid])
    ]
    assert len(breaks) == 20
    via_cp1d = [fid for fid, d in lineage.items() if any(x.startswith("cp1d:T1D.") for x in d)]
    assert len(via_cp1d) == 6
