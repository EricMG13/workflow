"""Stage 2 connection of CP-5 (integrity review): the owner extras and the G1 registration rows.

Expectations come from `docs/CP5-OWNER-LEASE.md` (Files, Public API additions) and
`docs/G1X-OWNER-CORE-PROTOCOL.md` section 2. CP-5 is live-contract: no `_CORES` row, no `SCHEMAS`,
no `RULES`. The store is a real `Execution` journal whose heads are the frozen Stage 1 fixture
(`tests/test_method_cp5.py`), so `review_scope`, the view and the probe run over real blobs.
The run assertions (`cp6_closed`, RT-1 to RT-3, D3) wait on the CP-6 freeze and are not here.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import test_method_cp5 as stage1

from deploy_vii import cp5_integrity
from deploy_vii.contracts import Fact, Module
from deploy_vii.cp5_integrity import IntegritySubmission, cp5_module
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    StepSubmission,
    current_inputs,
    head_of,
    settle,
)
from deploy_workflow import owner_workflow as owner
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.owners import cp5
from deploy_workflow.workflow import WorkflowError

CASES = stage1.CASES
STEP = "integrity_review"


@dataclass(frozen=True)
class Journal:
    store: Execution
    snapshot: ExecutionSnapshot
    attempt: Attempt
    payload: str


def _cp0_authorising(fixture: stage1.Fixture) -> Module:
    """The fixture CP-0 with the T8 command that authorises CP-5 (current_inputs needs it)."""
    command = Fact(
        fact_id="run-cp5",
        label="CP5 command",
        table_id="T8",
        row_id="CP-5",
        field="exact_command",
        text="Run CP-5",
    )
    cp0 = fixture.heads["CP-0"]
    return cp0.model_copy(update={"facts": (*cp0.facts, command)})


def _heads(case: str, blocked: str | None = None) -> dict[str, Module]:
    """The Stage 1 heads, rebuilt on the authorising CP-0 (every downstream hash follows it)."""
    fixture = stage1.make_fixture(case)
    pack = fixture.pack
    cp0 = _cp0_authorising(fixture)
    cp1 = stage1.make_cp1(pack, case, cp0)
    heads = {
        "CP-0": cp0,
        "CP-1": cp1,
        "CP-1A": stage1.make_cp1a(pack, case, cp1, None),
        "CP-2": stage1.make_cp2(pack, case, cp1),
        "CP-3": stage1.make_cp3(pack, case, cp1),
    }
    if blocked is not None:
        heads[blocked] = heads[blocked].model_copy(update={"status": "blocked"})
    return heads


def make_journal(
    tmp_path: Path, case: str, *, finished: bool = False, blocked: str | None = None
) -> Journal:
    pack = stage1.make_pack(case)
    store = Execution.create(tmp_path / "store", pack)
    heads = _heads(case, blocked)
    snapshot = store.read()
    head_rows = []
    for module in heads.values():
        store._store(module.model_dump_json())
        head_rows.append(head_of(module))
    snapshot = snapshot.model_copy(update={"heads": tuple(head_rows)})
    inputs = current_inputs(snapshot, "CP-5")
    submission = stage1._instantiate(stage1.SUBMISSIONS[case])
    step = StepSubmission(
        step_id=STEP, inputs=inputs, payload_sha256=store._store(submission), status="pending"
    )
    attempt = Attempt(ticket_id="t5", module_id="CP-5", inputs=inputs, number=0, steps=(step,))
    snapshot = snapshot.model_copy(update={"attempts": (attempt,)})
    store._write(snapshot)
    journal = Journal(store, snapshot, attempt, submission)
    return _finish(journal) if finished else journal


def _validated(journal: Journal) -> Journal:
    outcome = cp5.ENTRY_VALIDATOR(journal.store, journal.store.pack(), journal.attempt)
    assert outcome.output is not None, outcome.issues
    step = journal.attempt.steps[0].model_copy(
        update={"status": "valid", "output_sha256": journal.store._store(outcome.output)}
    )
    attempt = journal.attempt.model_copy(update={"steps": (step,)})
    snapshot = journal.snapshot.model_copy(update={"attempts": (attempt,)})
    journal.store._write(snapshot)
    return Journal(journal.store, snapshot, attempt, journal.payload)


def _finish(journal: Journal) -> Journal:
    """Settle CP-5 as the entry does: the validated step, then the Python candidate."""
    journal = _validated(journal)
    store, attempt = journal.store, journal.attempt
    output = store.step_output(attempt.steps[0].output_sha256 or "")
    candidate = cp5_module(
        cp5_integrity.IntegrityReport.model_validate_json(output), attempt.inputs, attempt.number
    )
    payload = candidate.model_dump_json()
    attempt = attempt.model_copy(update={"payload_sha256": store._store(payload)})
    finished, result = settle(
        journal.snapshot,
        attempt,
        payload,
        lambda supplied: () if supplied == candidate else ("Candidate differs",),
        pack=store.pack(),
        load=store.head_module,
    )
    store._store(result.model_dump_json())
    snapshot = journal.snapshot.model_copy(
        update={"attempts": (finished,), "heads": (*journal.snapshot.heads, head_of(result))}
    )
    store._write(snapshot)
    return Journal(store, snapshot, finished, journal.payload)


@pytest.fixture(params=CASES)
def pending(request: pytest.FixtureRequest, tmp_path: Path) -> Journal:
    return make_journal(tmp_path, request.param)


@pytest.fixture(params=CASES)
def settled(request: pytest.FixtureRequest, tmp_path: Path) -> Journal:
    return make_journal(tmp_path, request.param, finished=True)


# --- registration rows ---------------------------------------------------------------------------


def test_spec_row_is_the_lease_row() -> None:
    expected = owner.OwnerSpec(
        module_id="CP-5",
        steps=(
            owner.StepSpec(
                step_id=STEP,
                schema=IntegritySubmission,
                sources=False,
                extract=False,
                upstream_grant=None,
                inputs="module_context",
                rules="none",
            ),
        ),
        entry="model_payload",
        kind="analytical",
        publish=None,
    )
    assert owner.OWNER_SPECS["CP-5"] == expected
    owner._check_steps("CP-5", owner.OWNER_SPECS["CP-5"])


def test_registry_rows() -> None:
    assert {"CP-0", "CP-1", "CP-1A", "CP-2", "CP-5"} <= owner.SUPPORTED_ANALYTICAL
    assert owner._QUALIFICATION["CP-5"] is cp5_integrity.PROMOTED
    assert cp5.QUALIFICATION is cp5_integrity.PROMOTED
    assert owner._PROBES["CP-5"] is cp5.probe
    assert owner._VIEWS[STEP] is cp5.view
    assert owner._ENTRY_VALIDATORS["CP-5"] is cp5.ENTRY_VALIDATOR
    assert "CP-5" not in owner._CORES  # live-contract: no owner_core dispatch (lease L2)
    assert "CP-5" not in owner._PRECHECKS  # rules="none"


@pytest.mark.parametrize(
    "table", ["OWNER_SPECS", "_QUALIFICATION", "_PROBES", "_VIEWS", "_ENTRY_VALIDATORS"]
)
def test_rows_are_appended_last_and_earlier_rows_stay(table: str) -> None:
    rows = list(getattr(owner, table))
    key = STEP if table == "_VIEWS" else "CP-5"
    assert key in rows
    # Other modules append after CP-5 as they merge; here only the earlier rows' order is pinned.
    head = ["CP-0", "CP-1", "CP-1A", "CP-2"] if table in ("OWNER_SPECS", "_QUALIFICATION") else []
    assert [r for r in rows if r in head] == [r for r in head if r in rows]
    if table == "_VIEWS":
        assert rows.index("credit_synthesis") < rows.index(key)
    if table == "_PROBES":
        assert rows.index("CP-2") < rows.index(key)
    if table == "_ENTRY_VALIDATORS":
        assert rows.index("CP-2") < rows.index(key)
    if table == "OWNER_SPECS":
        assert rows.index("CP-MODEL") < rows.index(key)


def test_cp5_has_no_owner_only_parts() -> None:
    for name in ("STEP_IDS", "SCHEMAS", "RULES", "submit", "precheck"):
        assert not hasattr(cp5, name), name


# --- the entry validator adapter -------------------------------------------------------------------


def test_entry_validator_drops_the_pack_and_calls_the_core_validator(pending: Journal) -> None:
    got = cp5.ENTRY_VALIDATOR(pending.store, pending.store.pack(), pending.attempt)
    want = cp5_integrity._validate_step(pending.store, pending.attempt)
    assert got == want
    assert got.output is not None and not got.issues


def test_entry_validator_refuses_a_forged_payload(pending: Journal) -> None:
    payload = json.loads(pending.payload)
    payload["claim_reviews"] = payload["claim_reviews"][1:]  # one claim left unreviewed
    store, attempt = pending.store, pending.attempt
    step = attempt.steps[0].model_copy(update={"payload_sha256": store._store(json.dumps(payload))})
    outcome = cp5.ENTRY_VALIDATOR(
        store, store.pack(), attempt.model_copy(update={"steps": (step,)})
    )
    assert outcome.output is None and outcome.issues


def test_entry_validator_replays_on_a_frozen_view(pending: Journal) -> None:
    frozen = _FrozenExecution(pending.store, pending.snapshot)
    outcome = cp5.ENTRY_VALIDATOR(frozen, frozen.pack(), pending.attempt)
    assert outcome == cp5.ENTRY_VALIDATOR(pending.store, pending.store.pack(), pending.attempt)


# --- the view --------------------------------------------------------------------------------------


def test_view_is_the_stage1_view_body_of_the_journal_scope(pending: Journal) -> None:
    frozen = _FrozenExecution(pending.store, pending.snapshot)
    scope = cp5_integrity.review_scope(frozen, pending.attempt)
    assert not scope.issues
    digest, body = cp5.view(frozen, pending.attempt)
    assert (digest, body) == cp5.view_body(scope)


def test_view_matches_the_oracle_tree_counts_and_holds_no_quote(pending: Journal) -> None:
    frozen = _FrozenExecution(pending.store, pending.snapshot)
    digest, body = cp5.view(frozen, pending.attempt)
    block = json.loads(body)
    case = (
        "gap" if pending.payload == stage1._instantiate(stage1.SUBMISSIONS["gap"]) else "positive"
    )
    assert hashlib.sha256(body.encode()).hexdigest() == digest
    assert body == json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    modules = block["modules"]
    claims = [c for m in modules for c in m["claims"]]
    assert {
        "top": list(block),
        "sources[*]": stage1._keys(block["sources"]),
        "modules[*]": stage1._keys(modules),
        "modules[*].facts[*]": stage1._keys([f for m in modules for f in m["facts"]]),
        "modules[*].claims[*]": stage1._keys(claims),
        "modules[*].claims[*].citations[*]": stage1._keys(
            [x for c in claims for x in c["citations"]]
        ),
    } == stage1.VIEW["key_tree"]
    counts = stage1.VIEW["counts"][case]
    assert [m["module_id"] for m in modules] == counts["module_order"]
    assert block["claims_to_review"] == counts["claims_to_review"]
    assert block["python_findings"] == counts["python_findings"]
    assert "quote" not in set(stage1._keys_anywhere(block))
    scope = cp5_integrity.review_scope(frozen, pending.attempt)
    assert block["inherited_limitations"] == list(scope.inherited)


def test_view_refuses_a_stale_scope(pending: Journal) -> None:
    store = pending.store
    stale = pending.snapshot.model_copy(
        update={
            "heads": tuple(
                h.model_copy(update={"status": "stale"}) if h.module_id == "CP-2" else h
                for h in pending.snapshot.heads
            )
        }
    )
    store._write(stale)
    frozen = _FrozenExecution(store, stale)
    with pytest.raises(WorkflowError) as caught:
        cp5.view(frozen, pending.attempt)
    assert caught.value.code == "identity_mismatch"


# --- the probe -------------------------------------------------------------------------------------


def test_probe_accepts_the_settled_head(settled: Journal) -> None:
    cp5.probe(settled.store, settled.snapshot, settled.attempt)


def test_probe_refuses_a_forged_head(settled: Journal) -> None:
    store = settled.store
    forged = next(h for h in settled.snapshot.heads if h.module_id == "CP-5")
    module = store.head_module(forged)
    other = module.model_copy(update={"limitations": (*module.limitations, "Forged")})
    store._store(other.model_dump_json())
    heads = tuple(head_of(other) if h.module_id == "CP-5" else h for h in settled.snapshot.heads)
    snapshot = settled.snapshot.model_copy(update={"heads": heads})
    with pytest.raises(WorkflowError) as caught:
        cp5.probe(store, snapshot, settled.attempt)
    assert caught.value.code == "identity_mismatch"


def test_probe_refuses_a_forged_step_output(settled: Journal) -> None:
    store = settled.store
    step = settled.attempt.steps[0]
    bad = store._store(json.dumps({"forged": True}))
    attempt = settled.attempt.model_copy(
        update={"steps": (step.model_copy(update={"output_sha256": bad}),)}
    )
    with pytest.raises(WorkflowError) as caught:
        cp5.probe(store, settled.snapshot, attempt)
    assert caught.value.code == "identity_mismatch"


@pytest.mark.parametrize("shape", ["no_step", "pending_step", "two_steps"])
def test_probe_refuses_a_wrong_step_shape(settled: Journal, shape: str) -> None:
    step = settled.attempt.steps[0]
    steps = {
        "no_step": (),
        "pending_step": (
            step.model_copy(update={"status": "pending", "output_sha256": None, "issues": ()}),
        ),
        "two_steps": (step, step),
    }[shape]
    attempt = settled.attempt.model_copy(update={"steps": steps})
    with pytest.raises(WorkflowError) as caught:
        cp5.probe(settled.store, settled.snapshot, attempt)
    assert caught.value.code == "identity_mismatch"


# --- store-level acceptance items (lease Acceptance: refusals, tamper, stale, blocked, bytes) ------


def _tree(store: Execution) -> dict[str, str]:
    return {
        str(p.relative_to(store.directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(store.directory.rglob("*"))
        if p.is_file()
    }


def test_view_validator_and_probe_leave_the_store_bytes_unchanged(settled: Journal) -> None:
    before = _tree(settled.store)
    frozen = _FrozenExecution(settled.store, settled.snapshot)
    pending_step = settled.attempt.steps[0]
    cp5.view(frozen, settled.attempt.model_copy(update={"status": "pending"}))
    cp5.ENTRY_VALIDATOR(frozen, frozen.pack(), settled.attempt)
    cp5.probe(settled.store, settled.snapshot, settled.attempt)
    assert pending_step.status == "valid"
    assert _tree(settled.store) == before


def test_view_digest_follows_the_bound_heads(tmp_path: Path) -> None:
    """A forged read body is caught because the verifier recomputes the digest from the journal:
    it must depend on the heads, the case and the statuses, never be a fixed value."""
    digests = set()
    for index, case in enumerate(CASES):
        for blocked in (None, "CP-3"):
            journal = make_journal(tmp_path / f"{index}-{blocked}", case, blocked=blocked)
            frozen = _FrozenExecution(journal.store, journal.snapshot)
            digests.add(cp5.view(frozen, journal.attempt)[0])
    assert len(digests) == 4


def test_view_lists_a_blocked_optional_head_and_does_not_evaluate_it(tmp_path: Path) -> None:
    journal = make_journal(tmp_path, "positive", blocked="CP-3")
    frozen = _FrozenExecution(journal.store, journal.snapshot)
    block = json.loads(cp5.view(frozen, journal.attempt)[1])
    assert block["blocked_upstream"] == ["CP-3"]
    listed = {m["module_id"]: m for m in block["modules"]}
    assert listed["CP-3"]["status"] == "blocked"
    assert all(module != "CP-3" for module, _ in block["claims_to_review"])
    assert next(i for i in journal.attempt.inputs if i.input_id == "CP-3").status == "blocked"


def test_blocked_head_makes_the_submitted_review_invalid(tmp_path: Path) -> None:
    """The oracle review names CP-3 claims, and a blocked CP-3 is not evaluated: refused."""
    journal = make_journal(tmp_path, "positive", blocked="CP-3")
    outcome = cp5.ENTRY_VALIDATOR(journal.store, journal.store.pack(), journal.attempt)
    assert outcome.output is None and outcome.issues


def test_stale_binding_after_a_head_is_resettled(pending: Journal) -> None:
    """The attempt binds CP-2's hash at begin; a later head with another hash is a stale binding
    for the view, the validator and the probe's historical replay."""
    store = pending.store
    cp2 = store.head_module(next(h for h in pending.snapshot.heads if h.module_id == "CP-2"))
    newer = cp2.model_copy(update={"limitations": (*cp2.limitations, "Re-settled later")})
    store._store(newer.model_dump_json())
    heads = tuple(head_of(newer) if h.module_id == "CP-2" else h for h in pending.snapshot.heads)
    moved = pending.snapshot.model_copy(update={"heads": heads})
    store._write(moved)
    frozen = _FrozenExecution(store, moved)
    with pytest.raises(WorkflowError) as caught:
        cp5.view(frozen, pending.attempt)
    assert caught.value.code == "identity_mismatch"
    outcome = cp5.ENTRY_VALIDATOR(frozen, frozen.pack(), pending.attempt)
    assert outcome.output is None and outcome.issues


def test_stale_head_status_is_a_stale_binding(pending: Journal) -> None:
    store = pending.store
    heads = tuple(
        h.model_copy(update={"status": "stale"}) if h.module_id == "CP-1A" else h
        for h in pending.snapshot.heads
    )
    moved = pending.snapshot.model_copy(update={"heads": heads})
    with pytest.raises(WorkflowError):
        cp5.view(_FrozenExecution(store, moved), pending.attempt)
