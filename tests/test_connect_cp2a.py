"""CP-2A Stage 2: the connection of the Stage 1 core to the store, the registrations, the
bindings and the reader (`docs/CP2A-OWNER-LEASE.md`, `docs/G1X-OWNER-CORE-PROTOCOL.md`).

Expectations come from the lease and `cases/cp2a-owner/{expected,submissions}.json`, never from the
code under test. The CP-0 and CP-1 heads of the store runs here are hand-seeded `Module`s built from
the oracle's own CP-1 records, re-cited against the real financial pack (a genuine CP-1 promotion
is a Stage 5 run; `tests/test_owner_cp2a.py` and `tests/cp2a_runs.py` carry those).
"""

import hashlib
import importlib
import json
import random
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pytest
from test_method_cp2a import (
    EXPECTED,
    ISSUER,
    LTM,
    Q3,
    Q4,
    SUBMISSIONS,
    bind_payload,
    cp1_facts,
    fig_ids,
    inputs_for,
)

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.business_context import CP1_REFERENCES
from deploy_vii.contracts import Citation, Fact, Input, Module, ModuleView, Run, View
from deploy_vii.execution import Attempt, Execution, Head, Qualification, head_of
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import _PRESETS, _spec_of, fact_spelling
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.owners import cp2a
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("s1a_runs")

MAX_LINE = 600
MODULE = "CP-2A"
STEP = "downside_pathway"
SYNTHETIC = "Synthetic case; not real issuer qualification"
REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
REFUSAL_ISSUES = {r["id"]: r["expected_issues"] for r in EXPECTED["refusals"]}
RUN_LEVEL = [
    r["id"]
    for r in EXPECTED["refusals"]
    if not REFUSALS[r["id"]].get("composer_only") and r["id"] != "v17"
]


def _positive_payload() -> dict[str, Any]:
    facts = cp1_facts("positive")
    payload: dict[str, Any] = bind_payload(
        SUBMISSIONS["positive"]["downside_pathway"], fig_ids(facts)
    )
    return payload


def _submission() -> cp2a.DownsideSubmission:
    return cp2a.DownsideSubmission.model_validate_json(json.dumps(_positive_payload()))


# --- backlog: caller-quoting issue lines go through `clipped` (0d-c audit, protocol section 5) ---


def test_scenario_name_in_an_issue_line_is_clipped() -> None:
    payload = _positive_payload()
    long_name = "Quoted name " + "x" * 5000
    payload["scenarios"][0]["name"] = long_name
    payload["scenarios"][1]["name"] = long_name
    issues = cp2a.validate(inputs_for("positive", payload))
    duplicate = [i for i in issues if "duplicate scenario name" in i]
    assert duplicate and all(len(i) <= MAX_LINE for i in issues)


def test_prose_issue_quoting_the_payload_is_clipped() -> None:
    payload = _positive_payload()
    payload["assessment"]["rationale"] = "A bare figure of " + "7" * 5000 + " appears."
    issues = cp2a.validate(inputs_for("positive", payload))
    assert issues and all(len(i) <= MAX_LINE for i in issues), [len(i) for i in issues]


def test_base_period_and_label_lines_quoting_the_payload_are_clipped() -> None:
    payload = _positive_payload()
    payload["base_period"] = "Q" + "9" * 5000
    issues = cp2a.validate(inputs_for("positive", payload))
    assert issues and all(len(i) <= MAX_LINE for i in issues)
    payload = _positive_payload()
    payload["thresholds"] = [
        {**t, "label": "Watch level " + "x" * 5000} for t in payload["thresholds"][:2]
    ]
    issues = cp2a.validate(inputs_for("positive", payload))
    assert [i for i in issues if "appears more than once" in i]
    assert all(len(i) <= MAX_LINE for i in issues)


def test_the_join_of_a_raised_composition_is_bounded() -> None:
    """Backlog: `compute` raises on any issue; its message is the bounded list (20 lines and a
    count), not every line."""
    inputs = inputs_for("positive", _many_issue_payload())
    assert len(cp2a.validate(inputs)) > 20
    with pytest.raises(ValueError, match=r"further issues not listed") as caught:
        cp2a.compute(inputs)
    assert len(str(caught.value).split("; ")) == 21


def _many_issue_payload() -> dict[str, Any]:
    payload = _positive_payload()
    payload["gaps"] = [
        {
            "gap": f"Gap number {chr(97 + n)}",
            "why_it_matters": " ",
            "affected_analysis": " ",
            "severity": "Minor",
            "action": " ",
        }
        for n in range(8)
    ]
    return payload


# --- the plug-in parts that need no store (protocol section 2) ---------------------------------


def test_core_attributes_match_the_lease() -> None:
    assert cp2a.QUALIFICATION == Qualification(implementation="implemented")
    assert cp2a.PROMOTED == cp2a.QUALIFICATION
    assert cp2a.STEP_IDS == (STEP,)
    assert dict(cp2a.SCHEMAS) == {STEP: cp2a.DownsideSubmission}
    for name in ("probe", "view", "submit", "ENTRY_VALIDATOR"):
        assert callable(getattr(cp2a, name)), name
    # Rule mode `none`, no precheck (lease Files; ruling 1): nothing to register for either.
    assert not hasattr(cp2a, "RULES")
    assert not hasattr(cp2a, "precheck")
    # Q6 (stage 2 rulings): the CP-2A lease ships no reader; consumers keep their own.
    assert not hasattr(cp2a, "cp2a_reader")


@pytest.mark.parametrize("case", ["positive", "gap", "interest_undisclosed"])
def test_schemas_round_trip_and_give_the_tail_digest(case: str) -> None:
    ids = fig_ids(cp1_facts(case)) if case != "gap" else {}
    payload = json.dumps(bind_payload(SUBMISSIONS[case]["downside_pathway"], ids))
    parsed = cp2a.SCHEMAS[STEP].model_validate_json(payload)
    assert cp2a.SCHEMAS[STEP].model_validate_json(parsed.model_dump_json()) == parsed
    assert parsed.content_hash() == hashlib.sha256(parsed.model_dump_json().encode()).hexdigest()
    assert cp2a.SUBMISSION_INPUT == STEP.replace("_", "-") + "-submission"


# --- the store adapter ----------------------------------------------------------------------


def _pack(as_of: str | None = None) -> PreparedPack:
    base = runs.make_pack("positive")
    document = json.loads(base.run.model_dump_json())
    if as_of is not None:
        document["as_of"] = as_of
    document["pathway"] = "distressed_restructuring"
    document["requested_modules"] = [MODULE]
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=base.sources)


def _cite(pack: PreparedPack) -> tuple[Citation, ...]:
    financial = next(s for s in pack.sources if s.source_id == "financial")
    span = financial.spans[0]
    assert financial.sha256 is not None
    return (
        Citation(
            source_id="financial",
            source_sha256=financial.sha256,
            locator=span.locator,
            quote=span.text.strip()[:40],
        ),
    )


def _recited(pack: PreparedPack, facts: tuple[Fact, ...]) -> tuple[Fact, ...]:
    """The fixture facts, each citation replaced by a real quote of the financial pack (the
    store re-checks every citation a settled CP-2A fact copies)."""
    cite = _cite(pack)
    return tuple(f.model_copy(update={"citations": cite}) if f.citations else f for f in facts)


def _decoys(pack: PreparedPack) -> tuple[Fact, ...]:
    """CP-1 facts the adapter must not hand to the core: another T4.10 metric of the LTM
    column, and a fact of another table."""
    return (
        Fact(
            fact_id="decoy-metric",
            label="LTM Q4 25 (2025-01-01 to 2025-12-31) · net_debt",
            table_id="T4.10",
            row_id="net_debt",
            amount=Decimal(1),
            unit="MILLIONS",
            currency="USD",
            period=LTM,
            citations=_cite(pack),
        ),
        Fact(
            fact_id="decoy-other-table",
            label="Other table fact",
            table_id="T4.1",
            row_id="x",
            text="not T4.10",
        ),
    )


def seed(
    root: Path,
    case: str = "positive",
    *,
    decoys: bool = False,
    as_of: str | None = None,
    cp1_status: Literal["accepted", "restricted"] = "restricted",
) -> tuple[Execution, PreparedPack, tuple[Fact, ...]]:
    """A store whose CP-0 and CP-1 heads are hand-built settled modules (CP-0 authorizes CP-2A;
    CP-1 holds the oracle's T4.10 facts of `case` and its sibling columns)."""
    pack = _pack(as_of)
    store = Execution.create(root / "store", pack)
    facts = _recited(pack, cp1_facts(case))
    snapshot = store.read()
    run = pack.run
    common: dict[str, Any] = {"run_id": run.run_id, "issuer_id": run.issuer_id, "as_of": run.as_of}
    command = Fact(
        fact_id="cp0-run-cp2a",
        label="Run CP-2A",
        table_id="T8",
        row_id=MODULE,
        field="exact_command",
        text="Run CP-2A",
    )
    pack_input = Input(input_id="prepared-pack", sha256=snapshot.pack_sha256)
    cp0 = Module(
        **common, module_id="CP-0", status="accepted", inputs=(pack_input,), facts=(command,)
    )
    cp0_head = head_of(cp0)
    cp1 = Module(
        **common,
        module_id="CP-1",
        status=cp1_status,
        inputs=(pack_input, Input(input_id="CP-0", sha256=cp0_head.result_sha256)),
        facts=(*facts, *(_decoys(pack) if decoys else ())),
        limitations=(SYNTHETIC,) if cp1_status == "restricted" else (),
    )
    for module in (cp0, cp1):
        store._store(module.model_dump_json())
    store._write(
        snapshot.model_copy(
            update={"parent": snapshot.content_hash(), "heads": (cp0_head, head_of(cp1))}
        )
    )
    return store, pack, facts


def test_adapter_returns_the_stage_1_input_object_but_for_offered_periods(
    tmp_path: Path,
) -> None:
    """The adapter equals the Stage 1 `Inputs` over the same CP-1 facts in every field but one.
    `offered_periods` differs on purpose (round 5-6 L6): Stage 1 hands the core the three periods
    `(LTM, Q3, Q4)` its fixture states; the adapter offers only the periods the head supports
    (nine T4.10 facts each, a parsable label), in the head's order. The core's result is the
    same either way, since the submission's base period is offered in both."""
    store, pack, facts = seed(tmp_path)
    attempt = store.begin(MODULE)
    got = cp2a._inputs(pack, _submission(), cp2a.cp2a_upstream(store, attempt))
    stage_1 = inputs_for("positive", _positive_payload(), facts)
    assert stage_1.offered_periods == (LTM, Q3, Q4)
    assert got.offered_periods == (LTM, Q3)
    assert list(got.offered_periods) != list(stage_1.offered_periods)
    assert got == replace(stage_1, offered_periods=(LTM, Q3))
    assert got.names == (pack.run.issuer_name,)
    assert cp2a.compute(got) == cp2a.compute(stage_1)


def test_adapter_offers_the_head_order_not_a_sorted_one(tmp_path: Path) -> None:
    """The gap case's head states Q3 before the LTM column; the offer keeps that order."""
    store, pack, facts = seed(tmp_path, "gap")
    attempt = store.begin(MODULE)
    got = cp2a._inputs(pack, _submission(), cp2a.cp2a_upstream(store, attempt))
    assert got.offered_periods == (Q3, LTM)
    assert got.cp1_facts == facts


def test_adapter_drops_what_the_core_does_not_read(tmp_path: Path) -> None:
    store, pack, facts = seed(tmp_path, decoys=True)
    attempt = store.begin(MODULE)
    upstream = cp2a.cp2a_upstream(store, attempt)
    assert len(upstream.cp1) == len(facts) + 2
    inputs = cp2a._inputs(pack, _submission(), upstream)
    assert inputs.cp1_facts == facts and inputs.offered_periods == (LTM, Q3)


def test_a_period_missing_one_metric_or_unrecognised_is_not_offered() -> None:
    facts = cp1_facts("positive")
    short = tuple(f for f in facts if not (f.period == Q3 and f.row_id == "fcf"))
    assert tuple(b.period for b in cp2a.offered_bases(short)) == (LTM,)
    odd = tuple(
        f.model_copy(update={"period": "Unknown basis"}) if f.period == Q3 else f for f in facts
    )
    assert tuple(b.period for b in cp2a.offered_bases(odd)) == (LTM,)
    doubled = (*facts, facts[0].model_copy(update={"fact_id": "dup"}))
    assert tuple(b.period for b in cp2a.offered_bases(doubled)) == (Q3,)


def test_offered_kinds_come_from_one_derivation() -> None:
    bases = cp2a.offered_bases(cp1_facts("fixture_quarter_known"))
    assert {b.period: b.kind for b in bases} == {LTM: "ltm", Q3: "quarter", Q4: "quarter"}
    assert all(b.kind == cp2a.period_kind(b.period) for b in bases)


def test_stale_input_is_the_oracle_v17_issue(tmp_path: Path) -> None:
    """Lease ruling 3: the positive payload against a literal Upstream whose current CP-1 Input
    differs gives exactly one `Stale input CP-1` line."""
    store, pack, facts = seed(tmp_path)
    bound = store.begin(MODULE).inputs
    cp1_bound = next(i for i in bound if i.input_id == "CP-1")
    other = Input(
        input_id="CP-1",
        sha256=hashlib.sha256(b"cp2a-owner v17: a different CP-1 head").hexdigest(),
        status="restricted",
    )
    current = tuple(other if i.input_id == "CP-1" else i for i in bound)
    upstream = cp2a.Upstream(bound=bound, current=current, cp1=facts)
    issues = cp2a.validate_downside(pack=pack, submission=_submission(), upstream=upstream)
    refusal = next(r for r in EXPECTED["refusals"] if r["id"] == "v17")
    assert refusal["issue_prefix"] == "Stale input CP-1: bound restricted "
    assert other.sha256[:12] == "7b28303b61b0"
    assert issues == (
        f"{refusal['issue_prefix']}{cp1_bound.sha256[:12]}, current restricted 7b28303b61b0",
    )


def test_a_refused_current_inputs_text_is_a_stale_issue(tmp_path: Path) -> None:
    store, pack, facts = seed(tmp_path)
    bound = store.begin(MODULE).inputs
    upstream = cp2a.Upstream(bound=bound, current="Required upstream is unrun", cp1=facts)
    assert cp2a.validate_downside(pack=pack, submission=_submission(), upstream=upstream) == (
        "Stale inputs: Required upstream is unrun",
    )


def test_upstream_current_is_the_inputs_text_when_current_inputs_refuses(tmp_path: Path) -> None:
    store, _, _ = seed(tmp_path)
    attempt = store.begin(MODULE)
    snapshot = store.read()
    heads = tuple(h for h in snapshot.heads if h.module_id != "CP-1")
    stale = _FrozenExecution(store, snapshot.model_copy(update={"heads": heads}))
    upstream = cp2a.cp2a_upstream(stale, attempt)
    assert upstream.current == "Required upstream is unrun, stale or blocked"


# --- the journal: submit, the entry validator, probe ---------------------------------------


def _submit(store: Execution, attempt: Attempt, payload: str) -> Any:
    return cp2a.submit(store, attempt.ticket_id, STEP, payload, None)


def _settled(root: Path) -> tuple[Execution, PreparedPack, Attempt, Any]:
    store, pack, _ = seed(root)
    attempt = store.begin(MODULE)
    return store, pack, attempt, _submit(store, attempt, json.dumps(_positive_payload()))


def _head(store: Execution, module_id: str) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _finished(store: Execution, attempt: Attempt) -> Attempt:
    return next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)


def test_submit_settles_the_positive_head_with_the_tail_input(tmp_path: Path) -> None:
    store, pack, attempt, submitted = _settled(tmp_path)
    assert (submitted.nulls_resolved, submitted.prefilled, submitted.prefilled_kinds) == (
        (),
        (),
        (),
    )
    assert submitted.composition is None
    finished = _finished(store, attempt)
    assert finished.status == "finished" and finished.issues == ()
    head = _head(store, MODULE)
    assert head.status == "restricted" and head.qualification == cp2a.QUALIFICATION
    module = store.head_module(head)
    parsed = cp2a.DownsideSubmission.model_validate_json(submitted.payload)
    assert cp2a.SCHEMAS[STEP].model_validate_json(submitted.payload) == parsed
    assert module.inputs == (
        *attempt.inputs,
        Input(input_id="downside-pathway-submission", sha256=parsed.content_hash()),
    )
    assert tuple(t.table_id for t in module.tables) == (
        *(f"T2B.{n}" for n in range(1, 10)),
        CP1_REFERENCES,
    )
    composed = cp2a.compute(cp2a._inputs(pack, parsed, cp2a.cp2a_upstream(store, attempt)))
    assert module.facts == composed.facts and module.claims == composed.claims
    assert module.tables == composed.tables
    assert module.limitations == (*composed.limitations, SYNTHETIC)


def test_probe_rebuilds_the_settled_head(tmp_path: Path) -> None:
    store, _, attempt, _ = _settled(tmp_path)
    cp2a.probe(store, store.read(), _finished(store, attempt))


def test_probe_refuses_a_head_that_does_not_rebuild(tmp_path: Path) -> None:
    store, _, attempt, _ = _settled(tmp_path)
    snapshot, finished = store.read(), _finished(store, attempt)
    step = finished.steps[0]
    forged = {
        "another step output": step.model_copy(update={"output_sha256": "0" * 64}),
        "a step that is not valid": step.model_copy(update={"status": "invalid"}),
    }
    for name, forged_step in forged.items():
        with pytest.raises(WorkflowError) as caught:
            cp2a.probe(store, snapshot, finished.model_copy(update={"steps": (forged_step,)}))
        assert caught.value.code == "identity_mismatch", name
    with pytest.raises(WorkflowError) as two:
        cp2a.probe(store, snapshot, finished.model_copy(update={"steps": (step, step)}))
    assert two.value.code == "identity_mismatch"


def test_probe_refuses_a_head_whose_module_differs(tmp_path: Path) -> None:
    """Another retained submission under the same step cannot rebuild the head."""
    store, _, attempt, _ = _settled(tmp_path)
    snapshot, finished = store.read(), _finished(store, attempt)
    other = _positive_payload()
    other["assessment"]["rationale"] = "A different, figure-free rationale for the assessment."
    changed = store._store(json.dumps(other))
    step = finished.steps[0].model_copy(update={"payload_sha256": changed})
    with pytest.raises(WorkflowError) as caught:
        cp2a.probe(store, snapshot, finished.model_copy(update={"steps": (step,)}))
    assert caught.value.code == "identity_mismatch"


@pytest.mark.parametrize("rid", RUN_LEVEL)
def test_each_refusal_is_a_journaled_invalid_step_with_the_oracle_issues(
    rid: str, tmp_path: Path
) -> None:
    store, _, facts = seed(tmp_path)
    ids = fig_ids(facts)
    attempt = store.begin(MODULE)
    refusal = REFUSALS[rid]
    text = refusal.get("payload_text")
    if text is None:
        payload = refusal["payload"]
        if refusal.get("bind_placeholders", True):
            payload = bind_payload(payload, ids)
        text = json.dumps(payload)
    _submit(store, attempt, text)
    finished = _finished(store, attempt)
    want = [
        re.sub(r"\{\{FACT_ID:([a-z_]+)\}\}", lambda m: ids[m[1]], i) for i in REFUSAL_ISSUES[rid]
    ]
    assert finished.status == "finished" and list(finished.issues) == want
    assert finished.steps[0].status == "invalid"
    assert all(len(i) <= MAX_LINE for i in finished.issues)
    rejected = store.result(finished.result_sha256 or "")
    assert rejected.status == "rejected" and list(rejected.limitations) == want
    assert not [h for h in store.read().heads if h.module_id == MODULE]


def test_two_refusals_block_the_module(tmp_path: Path) -> None:
    """`expected.json` blocked: r01 settles rejected on attempt 0, v13 blocked on attempt 1."""
    store, _, facts = seed(tmp_path)
    expected = EXPECTED["cases"]["blocked"]
    first = store.begin(MODULE)
    _submit(store, first, json.dumps(REFUSALS["r01"]["payload"]))
    assert list(_finished(store, first).issues) == expected["attempt_0"]["limitations"]
    second = store.begin(MODULE)
    assert second.number == 1 and second.repair_of == first.ticket_id
    assert list(second.repair_issues) == expected["attempt_1"]["repair_issues"]
    _submit(store, second, json.dumps(bind_payload(REFUSALS["v13"]["payload"], fig_ids(facts))))
    head = _head(store, MODULE)
    module = store.head_module(head)
    assert head.status == "blocked" and module.status == "blocked"
    assert list(module.limitations) == expected["attempt_1"]["limitations"]
    assert module.tables == () and module.facts == ()


def test_submit_refuses_rules_and_a_foreign_step(tmp_path: Path) -> None:
    store, _, _ = seed(tmp_path)
    attempt = store.begin(MODULE)
    payload = json.dumps(_positive_payload())
    with pytest.raises(ValueError, match="rules"):
        cp2a.submit(store, attempt.ticket_id, STEP, payload, lambda text: ())
    with pytest.raises(ValueError, match="one step"):
        cp2a.submit(store, attempt.ticket_id, "other_step", payload, None)


def test_entry_validator_is_the_one_submit_journals_with(tmp_path: Path) -> None:
    store, pack, attempt, _ = _settled(tmp_path)
    finished = _finished(store, attempt)
    outcome = cp2a.ENTRY_VALIDATOR(store, pack, finished)
    assert outcome.issues == () and outcome.retained_as(finished.steps[0])


# --- the exact `read_inputs` view -------------------------------------------------------------

FORBIDDEN_KEYS = {"quote", "citations", "record_json"}
TREE_KEYS = {
    "upstream",
    "base_periods",
    "cp1_facts",
    "cp1_facts_note",
    "scenario_bounds",
    "threshold_metrics",
    "inherited_limitations",
}


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def test_view_is_the_lease_key_tree_without_quotes(tmp_path: Path) -> None:
    store, _, facts = seed(tmp_path)
    attempt = store.begin(MODULE)
    digest, body = cp2a.view(_FrozenExecution(store, store.read()), attempt)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    tree = json.loads(body)
    assert body == json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
    assert set(tree) == TREE_KEYS and not _keys(tree) & FORBIDDEN_KEYS
    assert [u["module_id"] for u in tree["upstream"]] == ["CP-0", "CP-1"]
    periods = [(p["period"], p["kind"]) for p in tree["base_periods"]]
    assert periods == [(LTM, "ltm"), (Q3, "quarter")]
    first = tree["base_periods"][0]
    assert set(first) == {"period", "kind", "operands", "ratios"}
    assert set(first["operands"]) == {
        "ebitda",
        "cash_interest",
        "fcf",
        "total_debt",
        "cash_closing",
    }
    assert set(first["ratios"]) == {
        "total_leverage",
        "net_leverage",
        "interest_coverage",
        "fcf_to_debt",
    }
    ebitda = next(f for f in facts if f.label.endswith("· ebitda") and f.period == LTM)
    assert first["operands"]["ebitda"] == {
        "ref": ebitda.fact_id,
        "shown": "30 US$ m",
        "status": "known",
        "limitation": None,
    }
    gated = tree["base_periods"][1]["ratios"]["total_leverage"]
    assert (gated["ref"], gated["shown"], gated["status"]) == (None, None, "missing")
    assert gated["limitation"]
    refs = {f["ref"] for f in tree["cp1_facts"]}
    assert refs <= {f.fact_id for f in facts} and ebitda.fact_id in refs
    assert set(tree["cp1_facts"][0]) == {"ref", "label", "period", "unit", "shown"}
    assert tree["scenario_bounds"] == {
        "decline": {"min": "0", "max": "1", "places": 4},
        "increase": {"min": "0", "max": "1", "places": 4},
    }
    assert tree["threshold_metrics"] == ["total_leverage", "net_leverage", "interest_coverage"]
    assert tree["inherited_limitations"] == [SYNTHETIC]


def test_view_is_the_registered_view_of_the_step(tmp_path: Path) -> None:
    store, _, _ = seed(tmp_path)
    attempt = store.begin(MODULE)
    frozen = _FrozenExecution(store, store.read())
    assert owner._VIEWS[STEP](frozen, attempt) == cp2a.view(frozen, attempt)


# --- registrations (lease Files; append-only rows) -------------------------------------------


def test_registrations_equal_the_lease() -> None:
    expected = owner.OwnerSpec(
        module_id=MODULE,
        steps=(
            owner.StepSpec(
                step_id=STEP,
                schema=cp2a.DownsideSubmission,
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
    assert owner._CORES[MODULE] is cp2a
    assert owner._QUALIFICATION[MODULE] is cp2a.QUALIFICATION
    assert owner._PROBES[MODULE] is cp2a.probe
    assert owner._VIEWS[STEP] is cp2a.view
    assert owner._ENTRY_VALIDATORS[MODULE] is cp2a.ENTRY_VALIDATOR
    assert MODULE not in owner._PRECHECKS
    owner._check_steps(MODULE, owner.OWNER_SPECS[MODULE])


def test_registrations_are_appended_after_the_shipped_rows() -> None:
    # CP-1D's row sits before CP-MODEL until its builder moves it: compare the base rows only.
    base = tuple(r for r in owner.OWNER_SPECS if r != "CP-1D")
    assert base[:5] == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._QUALIFICATION)[:4] == ("CP-1", "CP-1A", "CP-2", "CP-MODEL")
    assert tuple(owner._PROBES)[:4] == ("CP-0", "CP-1", "CP-1A", "CP-2")
    assert tuple(owner._VIEWS)[:1] == ("credit_synthesis",)
    assert tuple(owner._ENTRY_VALIDATORS)[:2] == ("CP-1A", "CP-2")


def test_a_plan_with_cp2a_passes_check_specs(tmp_path: Path) -> None:
    planned = owner._check_specs(_pack(), owner.OWNER_SPECS, None, tmp_path / "x")
    assert planned == ("CP-0", "CP-1", "CP-2A")


# --- bindings and the _Spec rows (lease D7) -----------------------------------------------------

BLOCKS = ("downside-stress", "break-points")


def test_preset_inserts_the_two_blocks_after_the_gate() -> None:
    """CP-2A's own pair, in order, right after `distress-gate`. Later modules insert their own
    ids after the pair and append `_Spec` rows (CP-2G lease :52, CP-4C lease :80), so nothing
    here pins the total length or an id outside the pair."""
    blocks = next(b for pid, _, _, b in _PRESETS if pid == "distressed_restructuring")
    gate = blocks.index("distress-gate")
    assert blocks[gate : gate + 3] == ("distress-gate", *BLOCKS)
    assert len(set(blocks)) == len(blocks)


def test_spec_rows_are_the_lease_composition() -> None:
    for block, title in zip(BLOCKS, ("Downside stress", "Break points"), strict=True):
        spec = _spec_of(block)
        assert (spec.title, spec.owner, spec.kind, spec.producers, spec.route_label) == (
            title,
            MODULE,
            "dense",
            (MODULE,),
            "Full analysis",
        )
    # An id no composition names keeps the idle wording (`_spec_of` falls through).
    assert _spec_of("no-such-block-id").owner == "Unbound"


def test_shipped_maps_hold_cp2a_once_after_cp6() -> None:
    """CP-2A lease: `SHIPPED_MAPS += CP2A`, so after the shipped maps; a later appender goes
    after it."""
    ids = [m.module_id for m in SHIPPED_MAPS]
    assert ids.count(MODULE) == 1
    assert ids.index(MODULE) > ids.index("CP-6")


def test_bindings_place_every_expected_table_exactly_once(tmp_path: Path) -> None:
    store, pack, _, _ = _settled(tmp_path)
    module = store.head_module(_head(store, MODULE))
    view = View(
        run=pack.run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Downside pathway",
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
    # Only CP-2A's map: the view holds only CP-2A, and a later module's map is not this test's.
    cp2a_map = next(m for m in SHIPPED_MAPS if m.module_id == MODULE)
    assert validate_bindings(view, (cp2a_map,)) == ()
    entries = cp2a_map.entries
    by_table = {e.fact_coord.table_id: e for e in entries}
    assert len(by_table) == len(entries)
    fp05 = EXPECTED["cases"]["positive"]["FP05"]
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
    assert set(by_table) == {*placed, *rails}
    assert all(e.cell_slot.startswith("cp2a-") for e in entries)


# --- the L6 offer rule as a property (round 5-6 L6; fix round 1 L2) --------------------------


def _perturbed(rng: random.Random, base: tuple[Fact, ...], periods: list[str]) -> tuple[Fact, ...]:
    facts = list(base)
    for _ in range(rng.randint(1, 3)):
        i = rng.randrange(len(facts))
        fact = facts[i]
        op = rng.randrange(7)
        if op == 0:
            facts.pop(i)
        elif op == 1:
            facts.append(fact.model_copy(update={"fact_id": f"{fact.fact_id}:dup{rng.random()}"}))
        elif op == 2:
            facts[i] = fact.model_copy(update={"period": rng.choice(periods)})
        elif op == 3:
            facts[i] = fact.model_copy(update={"period": "Odd basis: 2025-01-01 to 2025-12-31"})
        elif op == 4:
            head, _, span = rng.choice(periods).partition(": ")
            metric = fact.label.split(" · ")[-1]
            facts[i] = fact.model_copy(update={"label": f"{head} ({span}) · {metric}"})
        elif op == 5:
            facts[i] = fact.model_copy(update={"table_id": "T4.9"})
        else:
            twin = {"fact_id": f"{fact.fact_id}:t", "table_id": "T4.1"}
            facts.append(fact.model_copy(update=twin))
    return tuple(facts)


def _parses(period: str) -> bool:
    try:
        cp2a.period_kind(period)
        cp2a._column(period)
    except ValueError:
        return False
    return True


def _composes(facts: tuple[Fact, ...], period: str) -> cp2a.BaseOperands | None:
    try:
        return cp2a.BaseOperands.from_cp1(facts, period=period)
    except ValueError:
        return None


class _Run:
    issuer_name = ISSUER


class _Pack:
    run = _Run()


def test_a_period_is_offered_exactly_when_the_core_can_compose_it() -> None:
    """Over random corruptions of a CP-1 head: (A) a period is offered iff its label parses and
    `BaseOperands.from_cp1` succeeds on the whole head (nothing is dropped silently, nothing the
    core would raise on is offered); (B) the adapter's facts give `from_cp1` the same nine facts
    `offered_bases` chose, and `validate` never raises."""
    rng = random.Random(20261028)
    base = cp1_facts("fixture_quarter_known")
    periods = sorted({f.period for f in base if f.period})
    submission = _submission()
    for n in range(400):
        facts = _perturbed(rng, base, periods)
        offered = {b.period: b for b in cp2a.offered_bases(facts)}
        for period in {f.period for f in facts if f.period} | set(periods):
            expect = _parses(period) and _composes(facts, period) is not None
            assert expect == (period in offered), (n, period)
        pack: Any = _Pack()
        chosen = submission.model_copy(update={"base_period": next(iter(offered), LTM)})
        inputs = cp2a._inputs(pack, chosen, cp2a.Upstream(bound=(), current=(), cp1=facts))
        assert inputs.offered_periods == tuple(offered)
        for period, found in offered.items():
            operands = _composes(inputs.cp1_facts, period)
            assert operands is not None and tuple(operands.sources.values()) == found.facts
        cp2a.validate(inputs)


# --- staleness through the store, ordering, the CP-1 blob (fix round 1 L2, L4) ----------------


def _swap_cp1_head(store: Execution, limitation: str) -> str:
    """Replace the CP-1 head by another CP-1 module (as a re-run would) and return its hash."""
    snapshot = store.read()
    old = next(h for h in snapshot.heads if h.module_id == "CP-1")
    module = store.result(old.result_sha256).model_copy(update={"limitations": (limitation,)})
    store._store(module.model_dump_json())
    heads = tuple(head_of(module) if h.module_id == "CP-1" else h for h in snapshot.heads)
    store._write(snapshot.model_copy(update={"parent": snapshot.content_hash(), "heads": heads}))
    return module.content_hash()


def test_upstream_binds_the_attempt_and_reports_the_head_now(tmp_path: Path) -> None:
    store, pack, _ = seed(tmp_path)
    attempt = store.begin(MODULE)
    fresh = cp2a.cp2a_upstream(store, attempt)
    assert fresh.bound == attempt.inputs and fresh.current == attempt.inputs
    new_hash = _swap_cp1_head(store, "A re-run CP-1 head")
    upstream = cp2a.cp2a_upstream(store, attempt)
    assert upstream.bound == attempt.inputs
    assert isinstance(upstream.current, tuple) and upstream.current != upstream.bound
    old = next(i for i in attempt.inputs if i.input_id == "CP-1")
    assert upstream.cp1 == fresh.cp1  # the facts are the bound head's, not the new one's
    issues = cp2a.validate_downside(pack=pack, submission=_submission(), upstream=upstream)
    assert issues == (
        f"Stale input CP-1: bound restricted {old.sha256[:12]}, current restricted {new_hash[:12]}",
    )


def test_stale_lines_come_before_content_lines(tmp_path: Path) -> None:
    store, pack, _ = seed(tmp_path)
    attempt = store.begin(MODULE)
    _swap_cp1_head(store, "A re-run CP-1 head")
    payload = _positive_payload()
    payload["scenarios"][1]["name"] = payload["scenarios"][0]["name"]
    submission = cp2a.DownsideSubmission.model_validate_json(json.dumps(payload))
    issues = cp2a.validate_downside(
        pack=pack, submission=submission, upstream=cp2a.cp2a_upstream(store, attempt)
    )
    assert len(issues) == 2
    assert issues[0].startswith("Stale input CP-1: bound ")
    assert "duplicate scenario name" in issues[1]


def test_a_bound_cp1_input_that_is_not_a_cp1_module_is_refused(tmp_path: Path) -> None:
    store, _, _ = seed(tmp_path)
    attempt = store.begin(MODULE)
    cp0 = next(i for i in attempt.inputs if i.input_id == "CP-0")
    swapped = tuple(
        i.model_copy(update={"sha256": cp0.sha256}) if i.input_id == "CP-1" else i
        for i in attempt.inputs
    )
    with pytest.raises(ValueError, match="CP-1"):
        cp2a.cp2a_upstream(store, attempt.model_copy(update={"inputs": swapped}))


def test_the_view_states_the_oracle_unit_token_and_spelling(tmp_path: Path) -> None:
    """The `unit` a figure reference must use is `figure_unit`, not the raw fact unit."""
    store, _, facts = seed(tmp_path)
    attempt = store.begin(MODULE)
    _, body = cp2a.view(_FrozenExecution(store, store.read()), attempt)
    offered = {f["ref"]: f for f in json.loads(body)["cp1_facts"]}
    by_label = {f.label: f for f in facts}
    for name, figure in SUBMISSIONS["figures"].items():
        entry = offered[by_label[figure["cp1_label"]].fact_id]
        assert (entry["unit"], entry["shown"]) == (figure["unit_token"], figure["spelled"]), name


# --- the settled head against the oracle (A1: unit, shown, claims) -----------------------------


def test_settled_facts_and_claims_equal_the_oracle(tmp_path: Path) -> None:
    store, _, attempt, _ = _settled(tmp_path)
    module = store.head_module(_head(store, MODULE))
    case = EXPECTED["cases"]["positive"]
    ids = fig_ids(cp1_facts("positive"))
    mine = [f for f in module.facts if f.table_id != CP1_REFERENCES]
    assert [f.fact_id for f in mine] == [e["fact_id"] for e in case["facts"]]
    for fact, want in zip(mine, case["facts"], strict=True):
        assert fact.status == want["status"] and fact.unit == want.get("unit"), fact.fact_id
        assert fact.period == want.get("period") and fact.value_class == want.get("value_class")
        if fact.status == "known":
            assert fact_spelling(fact, None)[2] == want["shown"], fact.fact_id
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in case["claims"]]
    for claim, want in zip(module.claims, case["claims"], strict=True):
        assert claim.text == bind_payload(want["text"], ids), claim.claim_id
        assert claim.limitation == want["limitation"]
    assert attempt.number == 0


# --- A3 clones through the workflow, in seconds (lease Acceptance A3) --------------------------


def _workflow(root: Path) -> tuple[Any, Execution]:
    """A workflow at the CP-2A step over the hand-seeded CP-0 and CP-1 heads. The plan is the one
    module (`("CP-2A",)`), so the CP-0 and CP-1 history a receipt needs does not exist: receipt
    verification (A4) is the Stage 5 test's."""
    store, _, _ = seed(root)
    return owner.OwnerWorkflow(store, (MODULE,), None), store


def test_a3_pack_tools_are_refused_and_submit_before_read_is_not_permitted(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    call = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert (call["status"], call["error_code"], call["body"]) == ("refused", "not_permitted", None)
    with pytest.raises(WorkflowError) as unread:
        workflow.submit_review(json.dumps(_positive_payload()))
    assert unread.value.code == "not_permitted"
    assert [h.module_id for h in store.read().heads] == ["CP-0", "CP-1"]


def test_a3_a_changed_snapshot_between_read_and_submit_is_stale(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    workflow.read_inputs()
    store.interrupt(workflow._binding.ticket_id, "external change between read and submit")
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(json.dumps(_positive_payload()))
    assert caught.value.code == "stale_binding"


def test_a3_the_one_read_is_the_view_and_a_valid_submit_settles(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    read = workflow.read_inputs()
    assert (read["inputs_sha256"], read["body"]) == cp2a.view(
        _FrozenExecution(store, store.read()), store.read().attempts[-1]
    )
    outcome = workflow.submit_review(json.dumps(_positive_payload()))
    assert outcome["status"] == "valid" and outcome["issues"] == []
    assert _head(store, MODULE).status == "restricted"


def test_a3_an_unreplaced_figure_is_invalid(tmp_path: Path) -> None:
    workflow, _ = _workflow(tmp_path)
    workflow.read_inputs()
    text = json.dumps(SUBMISSIONS["positive"]["downside_pathway"])
    outcome = workflow.submit_review(text)
    assert outcome["status"] == "invalid"
    assert any("Malformed run text" in issue for issue in outcome["issues"]), outcome["issues"]


def test_the_settled_head_follows_the_run_not_the_oracle_constants(tmp_path: Path) -> None:
    """A different as_of and an accepted (not restricted) CP-1 head: the module carries them,
    the bound CP-1 input keeps its status, and no inherited limitation is invented."""
    store, pack, _ = seed(tmp_path, as_of="2026-03-31", cp1_status="accepted")
    attempt = store.begin(MODULE)
    _submit(store, attempt, json.dumps(_positive_payload()))
    head = _head(store, MODULE)
    module = store.head_module(head)
    assert module.as_of.isoformat() == "2026-03-31" == pack.run.as_of.isoformat()
    assert next(i for i in module.inputs if i.input_id == "CP-1").status == "accepted"
    assert head.status == "restricted"
    assert SYNTHETIC in module.limitations and module.inherited_limitations == ()
    _, body = cp2a.view(_FrozenExecution(store, store.read()), attempt)
    assert json.loads(body)["inherited_limitations"] == []
    assert {u["module_id"]: u["status"] for u in json.loads(body)["upstream"]}["CP-1"] == "accepted"


# --- units: a base is offered only in USD millions (Stage 2 round 5 item 1, CP-2A M2) ----------


@pytest.mark.parametrize(
    "update",
    [
        {"currency": "EUR"},
        {"unit": "THOUSANDS", "scale": Decimal(1000)},
        {"scale": Decimal(1000)},
        {"unit": "THOUSANDS"},
        {"currency": None},
    ],
)
@pytest.mark.parametrize("metric", ["ebitda", "cash_interest", "fcf", "total_debt", "cash_closing"])
def test_a_base_with_an_operand_outside_usd_millions_is_not_offered(
    metric: str, update: dict[str, Any]
) -> None:
    facts = cp1_facts("positive")
    changed = tuple(
        f.model_copy(update=update) if f.period == LTM and f.row_id == metric else f for f in facts
    )
    assert tuple(b.period for b in cp2a.offered_bases(changed)) == (Q3,)


def test_an_unsettled_operand_in_another_unit_does_not_unoffer_the_base() -> None:
    """Only a known operand's unit is read; a missing one carries no amount (a gap, never 0)."""
    facts = cp1_facts("interest_undisclosed")
    assert any(f.status != "known" and f.row_id == "cash_interest" for f in facts)
    other = tuple(
        f.model_copy(update={"unit": None, "currency": None, "scale": Decimal(1)})
        if f.status != "known" and f.row_id == "cash_interest"
        else f
        for f in facts
    )
    periods = tuple(b.period for b in cp2a.offered_bases(facts))
    assert periods and tuple(b.period for b in cp2a.offered_bases(other)) == periods


def test_the_adapter_refuses_a_euro_thousands_base_as_not_offered(tmp_path: Path) -> None:
    store, pack, facts = seed(tmp_path)
    eur = tuple(
        f.model_copy(update={"currency": "EUR", "unit": "THOUSANDS", "scale": Decimal(1000)})
        if f.period == LTM and f.unit == "MILLIONS"
        else f
        for f in facts
    )
    upstream = cp2a.Upstream(bound=store.begin(MODULE).inputs, current=(), cp1=eur)
    submission = _submission()
    inputs = cp2a._inputs(pack, submission, upstream)
    assert inputs.offered_periods == (Q3,)
    issues = cp2a.validate(inputs)
    assert issues == (f"base_period: not an offered period: {LTM}",)


# --- remaining reviewer survivors (fix round 1 L2) ---------------------------------------------


def test_the_adapter_keeps_the_heads_fact_order(tmp_path: Path) -> None:
    store, pack, facts = seed(tmp_path)
    upstream = cp2a.Upstream(bound=store.begin(MODULE).inputs, current=(), cp1=facts[::-1])
    inputs = cp2a._inputs(pack, _submission(), upstream)
    assert inputs.cp1_facts == facts[::-1] and inputs.offered_periods == (Q3, LTM)


def test_a_stale_line_names_a_status_change_with_the_same_hash(tmp_path: Path) -> None:
    store, pack, facts = seed(tmp_path)
    bound = store.begin(MODULE).inputs
    current = tuple(
        i.model_copy(update={"status": "accepted"}) if i.input_id == "CP-1" else i for i in bound
    )
    sha = next(i.sha256 for i in bound if i.input_id == "CP-1")[:12]
    upstream = cp2a.Upstream(bound=bound, current=current, cp1=facts)
    assert cp2a.validate_downside(pack=pack, submission=_submission(), upstream=upstream) == (
        f"Stale input CP-1: bound restricted {sha}, current accepted {sha}",
    )


def test_a_refused_current_inputs_text_is_clipped(tmp_path: Path) -> None:
    store, pack, facts = seed(tmp_path)
    upstream = cp2a.Upstream(bound=store.begin(MODULE).inputs, current="x" * 5000, cp1=facts)
    issues = cp2a.validate_downside(pack=pack, submission=_submission(), upstream=upstream)
    assert len(issues) == 1 and len(issues[0]) <= MAX_LINE


def test_the_view_shows_a_known_operand_it_does_not_let_the_analyst_cite(tmp_path: Path) -> None:
    """A known fact with neither citation nor calculation is shown but has no ref and is not in
    `cp1_facts`; with no citable fact at all the note says no figure may be written."""
    store, pack, facts = seed(tmp_path)
    bare = tuple(f.model_copy(update={"citations": (), "calculation_id": None}) for f in facts)
    bound = store.begin(MODULE).inputs
    tree: Any = cp2a.context_block(
        pack=pack, upstream=cp2a.Upstream(bound=bound, current=bound, cp1=bare)
    )
    first: Any = tree["base_periods"][0]
    cell = first["operands"]["ebitda"]
    assert cell["ref"] is None and cell["shown"] == "30 US$ m" and cell["status"] == "known"
    assert tree["cp1_facts"] == []
    assert "no figure may be referenced" in str(tree["cp1_facts_note"])
