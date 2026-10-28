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
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

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
from deploy_vii.report_view import _PRESETS, _spec_of
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


def _pack() -> PreparedPack:
    base = runs.make_pack("positive")
    document = json.loads(base.run.model_dump_json())
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
    root: Path, case: str = "positive", *, decoys: bool = False
) -> tuple[Execution, PreparedPack, tuple[Fact, ...]]:
    """A store whose CP-0 and CP-1 heads are hand-built settled modules (CP-0 authorizes CP-2A;
    CP-1 holds the oracle's T4.10 facts of `case` and its sibling columns)."""
    pack = _pack()
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
        status="restricted",
        inputs=(pack_input, Input(input_id="CP-0", sha256=cp0_head.result_sha256)),
        facts=(*facts, *(_decoys(pack) if decoys else ())),
        limitations=(SYNTHETIC,),
    )
    for module in (cp0, cp1):
        store._store(module.model_dump_json())
    store._write(
        snapshot.model_copy(
            update={"parent": snapshot.content_hash(), "heads": (cp0_head, head_of(cp1))}
        )
    )
    return store, pack, facts


def test_adapter_returns_the_stage_1_input_object(tmp_path: Path) -> None:
    store, pack, facts = seed(tmp_path)
    attempt = store.begin(MODULE)
    got = cp2a._inputs(pack, _submission(), cp2a.cp2a_upstream(store, attempt))
    stage_1 = inputs_for("positive", _positive_payload(), facts)
    assert got == cp2a.Inputs(
        submission=stage_1.submission, cp1_facts=facts, offered_periods=(LTM, Q3), names=(ISSUER,)
    )
    assert got.names == (pack.run.issuer_name,)


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
        "another attempt number": finished.model_copy(update={"number": 1}),
        "another step output": finished.model_copy(
            update={"steps": (step.model_copy(update={"output_sha256": "0" * 64}),)}
        ),
        "two steps": finished.model_copy(update={"steps": (step, step)}),
    }
    # The shared `probe_one_step` raises `identity_mismatch`, or the settlement's own ValueError
    # for a candidate that is not the retained payload; the receipt verifier maps both.
    for name, forged_attempt in forged.items():
        with pytest.raises((WorkflowError, ValueError)):
            cp2a.probe(store, snapshot, forged_attempt)
        assert name


def test_probe_refuses_a_head_whose_module_differs(tmp_path: Path) -> None:
    """Another retained submission under the same step cannot rebuild the head."""
    store, _, attempt, _ = _settled(tmp_path)
    snapshot, finished = store.read(), _finished(store, attempt)
    other = _positive_payload()
    other["assessment"]["rationale"] = "A different, figure-free rationale for the assessment."
    changed = store._store(json.dumps(other))
    step = finished.steps[0].model_copy(update={"payload_sha256": changed})
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp2a.probe(store, snapshot, finished.model_copy(update={"steps": (step,)}))


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
    assert tuple(owner.OWNER_SPECS)[:5] == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL")
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
    blocks = next(b for pid, _, _, b in _PRESETS if pid == "distressed_restructuring")
    assert blocks[:4] == ("distress-gate", *BLOCKS, "recovery-by-class")
    assert len(blocks) == 13


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
    assert _spec_of("recovery-by-class").owner == "Unbound"


def test_shipped_maps_end_with_cp2a() -> None:
    assert SHIPPED_MAPS[-1].module_id == MODULE
    assert len(SHIPPED_MAPS) == 11


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
    assert validate_bindings(view, SHIPPED_MAPS) == ()
    entries = SHIPPED_MAPS[-1].entries
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
