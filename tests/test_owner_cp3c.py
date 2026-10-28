"""CP-3C acceptance (docs/CP3C-OWNER-LEASE.md: Refusals, Tool use, Acceptance; expected.json
`negative_cases`, `tool_use`, `tamper`, `consumption`, `cp1_downstream_readiness`).

Two groups. The fast group drives the real `OwnerWorkflow` over the synthetic store of
`test_connect_cp3c` (CP-0, CP-1, CP-1A and CP-2 settled from records, CP-2D by its own core,
`OwnerWorkflow(store, ("CP-3C",), None)`): the read, the refused invoke, the premature submit,
the stale binding, the inputs, the blocked walk, the refused begin and model text at run level.
The store-run group needs a real CP-1 promotion (11 to 26 minutes) and a receipt over the full
plan, so it is written here and run only with `CP3C_STORE_RUNS=1` (Stage 5): the three store
runs against the oracle, the receipt verifier, store bytes unchanged, the CP-1 readiness
re-assertion, D3 and the reader on the closed heads, the blocked and refused-begin receipts and
the tamper test. A7 (the rendered page) waits for G2 Stage 3 and the D7 ruling.
"""

import hashlib
import importlib
import json
import os
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as tc2d
import test_connect_cp3c as tc
import test_method_cp2d as tm2d
import test_method_cp3c as tm
from defect_classes import model_text_failures

from deploy_vii.contracts import Input
from deploy_vii.downstream_readiness import DownstreamReport, validate_downstream_review
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, head_of
from deploy_workflow.owner_workflow import BLOCKED_EDGE, OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.owners import cp3c
from deploy_workflow.workflow import WorkflowError

ow: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("cp3c_runs")

MODULE = tc.MODULE
# The attempt binds CP-1A too (registry.dependencies selects the optional producer the run plans);
# the oracle's attempt_inputs omit it (test_connect_cp3c.CP1A_BOUND; reported to LEAD).
BOUND = ("CP-0", "CP-1", tc.CP1A_BOUND, "CP-2D")
NEGATIVE = tm.EXPECTED["negative_cases"]

# --- the fast group: the real workflow over the synthetic store ---------------------------------


def _workflow(root: Path, case: str = "positive", **kwargs: Any) -> tuple[OwnerWorkflow, Execution]:
    store, _ = tc.make_store(root, case, **kwargs)
    return OwnerWorkflow(store, (MODULE,), None), store


def _pending(store: Execution) -> Attempt:
    return next(a for a in store.read().attempts if a.module_id == MODULE and a.status == "pending")


def _payload(store: Execution, case: str = "positive") -> str:
    return tc.literal(store, _pending(store), case)


def _bound(store: Execution, payload: Any) -> str:
    return json.dumps(tc.bound_payload(payload, tc.refs(store, _pending(store))))


def test_the_step_is_session_less_and_the_walk_begins_cp3c(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    assert workflow._session is None and workflow._binding.module_id == MODULE
    assert workflow._binding.step_id == cp3c.STEP_ID and workflow._spec.inputs == "module_context"
    assert [a.module_id for a in store.read().attempts if a.status == "pending"] == [MODULE]


def test_every_invoke_is_a_refused_receipt_and_no_call_is_ok(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    payload = _payload(store)
    for tool, arguments in (
        ("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}),
        ("search_pack", {"query": "maturity", "source_id": "financial"}),
    ):
        call = workflow.invoke(tool, arguments)
        assert (call["status"], call["error_code"], call["body"]) == (
            "refused",
            "not_permitted",
            None,
        )
    workflow.read_inputs()
    assert workflow.submit_review(payload)["status"] == "valid"
    assert workflow._calls and all(c.status != "ok" for c in workflow._calls)


def test_submit_before_read_inputs_is_not_permitted(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    payload, before = _payload(store), store.read().content_hash()
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(payload)
    assert caught.value.code == "not_permitted"
    assert store.read().content_hash() == before  # nothing was journaled


def test_read_inputs_body_is_the_exact_view_and_is_counted(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    record = workflow.read_inputs()
    digest, body = cp3c.view(store, _pending(store))
    assert (record["inputs_sha256"], record["body"]) == (digest, body)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    assert list(json.loads(body)) == tc.TREE["top_level_keys_in_order"]
    assert [(r.binding.module_id, r.inputs_sha256) for r in workflow._reads] == [(MODULE, digest)]


def test_a_snapshot_change_between_read_and_submit_is_stale_binding(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    payload = _payload(store)
    workflow.read_inputs()
    store.interrupt(workflow._binding.ticket_id, "external change between read and submit")
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(payload)
    assert caught.value.code == "stale_binding"


def _expected_inputs(snapshot: ExecutionSnapshot) -> tuple[Input, ...]:
    heads = {h.module_id: h for h in snapshot.heads}
    return (
        Input(input_id="prepared-pack", sha256=snapshot.pack_sha256),
        *(
            Input.model_validate(
                {"input_id": m, "sha256": heads[m].result_sha256, "status": heads[m].status}
            )
            for m in BOUND
        ),
    )


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_inputs_are_hash_equal_to_the_final_heads_plus_the_tail(tmp_path: Path, case: str) -> None:
    workflow, store = _workflow(tmp_path, case)
    payload = _payload(store, case)
    workflow.read_inputs()
    assert workflow.submit_review(payload)["status"] == "valid"
    snapshot = store.read()
    expected = _expected_inputs(snapshot)
    attempt = next(a for a in snapshot.attempts if a.module_id == MODULE)
    assert attempt.inputs == expected
    h = tc.head(store, MODULE)
    module = store.head_module(h)
    tail = cp3c.RefinancingRiskSubmission.model_validate_json(payload).content_hash()
    assert module.inputs == (*expected, Input(input_id=cp3c.SUBMISSION_INPUT, sha256=tail))
    assert h == head_of(module, cp3c.QUALIFICATION) and h.status == "restricted"


def test_blocked_cp3c_walks_to_a_blocked_head_and_the_reader_has_status_only(
    tmp_path: Path,
) -> None:
    workflow, store = _workflow(tmp_path)
    blocked, issues = tm.SUBMISSIONS["cp3c_blocked"], NEGATIVE["blocked_cp3c"]
    for name in ("attempt_0", "attempt_1"):
        text = _bound(store, blocked[name])
        workflow.read_inputs()
        outcome = workflow.submit_review(text)
        assert (outcome["status"], outcome["issues"]) == ("invalid", issues[name]["issues"])
    assert workflow._phase == "complete"
    h = tc.head(store, MODULE)
    assert h.status == issues["module_status"] == "blocked"
    assert cp3c.cp3c_reader(store, h) == cp3c.Cp3cHead("blocked", h.result_sha256)
    module = store.head_module(h)
    assert not module.facts and not module.tables and not module.claims


def test_begin_is_refused_when_cp2d_is_blocked_and_no_attempt_is_consumed(tmp_path: Path) -> None:
    blocked = tm2d.SUBMISSIONS["cp2d_blocked"]
    literals = tuple(json.dumps(tm2d._bind(blocked[a])) for a in ("attempt_0", "attempt_1"))
    store, _ = tc.make_store(tmp_path, cp2d_literals=literals)
    assert tc.head(store, "CP-2D").status == "blocked"
    workflow = OwnerWorkflow(store, (MODULE,), None)
    (refusal,) = workflow._refusals
    assert refusal.module_id == MODULE and refusal.reason.startswith(BLOCKED_EDGE)
    want = NEGATIVE["begin_refused_cp2d_blocked"]["cp2d_attempt_1_submit_outcome"]["refusal"]
    assert workflow._refusal_code() == want and workflow._phase == "complete"
    assert [a for a in store.read().attempts if a.module_id == MODULE] == []
    assert not any(h.module_id == MODULE for h in store.read().heads)


def test_a_stale_required_head_is_not_a_retained_refusal(tmp_path: Path) -> None:
    """Only the blocked half of 'a stale or blocked producer refuses the begin' is a retained
    refusal; a stale one re-raises at begin (owner_workflow `_begin`) and consumes no attempt."""
    store, pack = tc.make_store(tmp_path)
    store.replace_pack(pack.model_copy(update={"sources": pack.sources[:1]}))
    assert {h.status for h in store.read().heads} == {"stale"}
    with pytest.raises(ValueError, match=BLOCKED_EDGE):
        OwnerWorkflow(store, (MODULE,), None)
    assert [a for a in store.read().attempts if a.module_id == MODULE] == []


class _Fresh:
    """One fresh copy of a store with CP-2D settled and CP-3C unbegun, walked by the real
    workflow, per hostile value (`model_text_failures`)."""

    template: Path
    root: Path
    made = 0

    def __init__(self) -> None:
        _Fresh.made += 1
        target = self.root / f"run{_Fresh.made}"
        shutil.copytree(self.template, target)
        self.store = Execution(target)
        self.workflow = OwnerWorkflow(self.store, (MODULE,), None)

    def submit_review(self, text: str) -> dict[str, Any]:
        self.workflow.read_inputs()
        outcome: dict[str, Any] = self.workflow.submit_review(text)
        return outcome


# Each literal carries one of `repricing` and `repricing_absence`, so each case's verbatim set is
# the patterns its payload has; the two cases together cover every pattern.
_ABSENT = {"positive": "repricing_absence", "gap_no_repricing": "repricing"}


@pytest.mark.parametrize("case", sorted(_ABSENT))
def test_model_text_is_refused_or_verbatim_and_never_wedges(case: str, tmp_path: Path) -> None:
    """Round 3 item 2 and round 5 item 10 at run level (the validator form is
    `test_connect_cp3c.test_model_text_is_stored_verbatim_on_every_free_text_path`)."""
    tc.make_store(tmp_path / "template", case)
    _Fresh.template, _Fresh.root = tmp_path / "template" / "store", tmp_path
    probe = _Fresh()
    positive = _payload(probe.store, case)
    verbatim = frozenset(p for p in tc.CP3C_VERBATIM if p[0] != _ABSENT[case])
    failures = model_text_failures(
        cp3c.RefinancingRiskSubmission, positive, _Fresh, verbatim=verbatim
    )
    assert failures == []


# --- the store-run group (CP-1 promotion; Stage 5) ----------------------------------------------

STORE_RUNS = pytest.mark.skipif(
    os.environ.get("CP3C_STORE_RUNS") != "1", reason="needs a real CP-1 promotion (Stage 5)"
)
Closed = tuple[Path, OwnerRunReceipt]


def _tree(*roots: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file()
    }


@pytest.fixture(scope="module")
def reached(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    workflow: OwnerWorkflow = runs.reach_cp2d(tmp_path_factory.mktemp("cp3c-reached"))[0]
    return workflow


@pytest.fixture(scope="module")
def closed(reached: OwnerWorkflow, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Closed]:
    out: dict[str, Closed] = {}
    for case in tm.PACK_CASES:
        root = tmp_path_factory.mktemp(f"cp3c-{case}")
        _, receipt = runs.cp3c_closed(case, root, reached)
        out[case] = (root, OwnerRunReceipt.model_validate_json(receipt.read_bytes()))
    return out


def _assert_cp2d_head_equals_its_oracle(store: Execution, cp2d_case: str) -> None:
    facts = {f.fact_id: f for f in store.head_module(tc.head(store, "CP-2D")).facts}
    for table in tm2d.CASES[cp2d_case]["tables"].values():
        for _, cells in table["rows"]:
            for cell in cells if isinstance(cells, list) else [cells]:
                tc2d._assert_fact(facts[cell["fact_id"]], cell, cp2d_case)


@STORE_RUNS
@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_store_run_heads_equal_the_oracle_and_the_receipt_verifies(
    closed: dict[str, Closed], case: str
) -> None:
    """A1 and A2: plan inputs, upstream statuses, the CP-0 consumer facts, the CP-2D head against
    its own oracle, every T3D table, ledger and claim, own limitations, the tail input; the
    receipt verifies and leaves the store bytes unchanged; no ok call and one read."""
    root, receipt = closed[case]
    store = Execution(root / "store")
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    want = tm.EXPECTED["cases"][case]
    attempt = next(a for a in snapshot.attempts if a.module_id == MODULE)
    assert attempt.inputs == _expected_inputs(snapshot)
    assert {heads[m].status for m in ("CP-0", "CP-1", "CP-2D")} == {"restricted"}
    assert heads[MODULE].status == want["status"]
    cp0 = {f.fact_id: f for f in store.head_module(heads["CP-0"]).facts}
    for fact in tm.EXPECTED["cp0_with_cp3c"]["added_facts_cp3c"]:
        got = cp0[fact["fact_id"]]
        assert got.text == fact["text"], fact["fact_id"]
        assert [[c.source_id, c.locator] for c in got.citations] == fact["cites"], fact["fact_id"]
    _assert_cp2d_head_equals_its_oracle(store, want["consumes_cp2d_case"])
    module = store.head_module(heads[MODULE])
    assert module.inputs[:-1] == attempt.inputs
    assert module.inputs[-1].input_id == cp3c.SUBMISSION_INPUT
    tc.assert_module_equals_oracle(module, case)
    assert list(module.limitations) == [*want["own_limitations"], tc.SYNTHETIC]
    before = _tree(root / "store")
    runs.verify_receipt(root / "store", receipt)
    assert _tree(root / "store") == before
    assert [c for c in receipt.calls if c.binding.module_id == MODULE and c.status == "ok"] == []
    (read,) = (r for r in receipt.input_reads if r.binding.module_id == MODULE)
    assert read.inputs_sha256 == hashlib.sha256(read.body.encode()).hexdigest()
    assert list(json.loads(read.body)) == tc.TREE["top_level_keys_in_order"]


@STORE_RUNS
def test_store_run_cp1_readiness_reassertion(closed: dict[str, Closed]) -> None:
    """The CP-1 downstream review this run ships validates on the promoted head's readiness
    inputs, and the requested consumers carry the oracle's statuses. A mismatch goes to LEAD;
    the oracle is not edited."""
    store = Execution(closed["positive"][0] / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    step = next(s for s in attempt.steps if s.step_id == "readiness")
    report = DownstreamReport.model_validate_json(store.step_output(step.output_sha256 or ""))
    oracle = tm.EXPECTED["cp1_downstream_readiness"]
    issues = list(validate_downstream_review(report.inputs, report.review))
    assert issues == oracle["validate_downstream_review"]
    rows = {r.canonical_module: r.status for r in report.consumers}
    assert {m: rows[m] for m in oracle["consumer_status"]} == oracle["consumer_status"]


@STORE_RUNS
@pytest.mark.parametrize("case", ["positive", "gap_minimum_cash"])
def test_store_run_d3_and_the_reader_on_the_closed_heads(
    closed: dict[str, Closed], case: str
) -> None:
    store = Execution(closed[case][0] / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    tc.assert_consumes_cp2d(store, attempt, case)
    h = tc.head(store, MODULE)
    assert cp3c.cp3c_reader(store, h) == tc.expected_read(h, case)


@STORE_RUNS
def test_store_run_submit_before_read_and_stale_binding(
    reached: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = runs.reach(tmp_path, reached)
    payload = runs.oracle()["submissions"]["cp3c"]["positive"]
    probe = runs.s1a.clone_workflow(workflow, tmp_path / "probe")
    text = runs.bind_facts(json.dumps(payload), json.loads(probe.read_inputs()["body"]))
    with pytest.raises(WorkflowError) as early:
        workflow.submit_review(text)
    assert early.value.code == "not_permitted"
    workflow.read_inputs()
    Execution(tmp_path / "store").interrupt(workflow._binding.ticket_id, "external change")
    with pytest.raises(WorkflowError) as stale:
        workflow.submit_review(text)
    assert stale.value.code == "stale_binding"


@STORE_RUNS
def test_store_run_blocked_cp3c_has_a_verifying_receipt_and_a_status_only_reader(
    reached: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow, outcomes = runs.blocked_cp3c(tmp_path, reached)
    blocked = NEGATIVE["blocked_cp3c"]
    assert [(o["status"], o["issues"]) for o in outcomes] == [
        ("invalid", blocked[a]["issues"]) for a in ("attempt_0", "attempt_1")
    ]
    receipt = OwnerRunReceipt.model_validate_json(runs.seal(workflow, tmp_path).read_bytes())
    runs.verify_receipt(tmp_path / "store", receipt)
    store = Execution(tmp_path / "store")
    h = tc.head(store, MODULE)
    assert h.status == "blocked"
    assert cp3c.cp3c_reader(store, h) == cp3c.Cp3cHead("blocked", h.result_sha256)


@STORE_RUNS
def test_store_run_begin_refused_cp2d_blocked_consumes_no_attempt(
    reached: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow, outcome = runs.begin_refused_cp2d_blocked(tmp_path, reached)
    want = NEGATIVE["begin_refused_cp2d_blocked"]["cp2d_attempt_1_submit_outcome"]
    assert {k: outcome[k] for k in want} == want
    receipt = OwnerRunReceipt.model_validate_json(runs.seal(workflow, tmp_path).read_bytes())
    runs.verify_receipt(tmp_path / "store", receipt)
    (refusal,) = receipt.refusals
    assert refusal.module_id == MODULE and refusal.reason.startswith(BLOCKED_EDGE)
    snapshot = Execution(tmp_path / "store").read()
    assert refusal.snapshot_sha256 == snapshot.content_hash()
    assert [a for a in snapshot.attempts if a.module_id == MODULE] == []
    assert not any(h.module_id == MODULE for h in snapshot.heads)


def _forge(store_path: Path, receipt: OwnerRunReceipt) -> tuple[Execution, OwnerRunReceipt]:
    """`expected.json#tamper.recipe`: T3D.2.r02 10 -> 11 in the CP-3C result Module, then every
    hash that names it (blob, snapshot, head, attempt, receipt, the settling submission record,
    the seal) rewritten."""
    tamper = tm.EXPECTED["tamper"]
    store = Execution(store_path)
    snapshot = store.read()
    old = tc.head(store, MODULE)
    module = store.head_module(old)
    target = next(f for f in module.facts if f.fact_id == tamper["target_fact"])
    assert target.amount == Decimal(tamper["from"])
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"amount": Decimal(tamper["to"])})
                if f.fact_id == target.fact_id
                else f
                for f in module.facts
            )
        }
    )
    new_sha = store._store(forged.model_dump_json())
    assert new_sha == forged.content_hash()
    assert head_of(forged, cp3c.QUALIFICATION).result_sha256 == new_sha
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == old.result_sha256)
    new_snapshot = snapshot.model_copy(
        update={
            "heads": tuple(
                h.model_copy(update={"result_sha256": new_sha}) if h.module_id == MODULE else h
                for h in snapshot.heads
            ),
            "attempts": tuple(
                a.model_copy(update={"result_sha256": new_sha})
                if a.ticket_id == attempt.ticket_id
                else a
                for a in snapshot.attempts
            ),
        }
    )
    store._write(new_snapshot)
    digest = new_snapshot.content_hash()
    settling = next(
        s
        for s in receipt.submissions
        if s.binding.binding.module_id == MODULE
        and s.snapshot_after_sha256 == receipt.snapshot_sha256
    )
    edited = settling.model_copy(update={"snapshot_after_sha256": digest})
    audit = store_path / ow.AUDIT / "submissions"
    (audit / settling.content_hash()).unlink()
    (audit / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    forged_receipt = receipt.model_copy(
        update={
            "snapshot_sha256": digest,
            "heads": tuple(
                h.model_copy(update={"result_sha256": new_sha}) if h.module_id == MODULE else h
                for h in receipt.heads
            ),
            "submissions": tuple(edited if s is settling else s for s in receipt.submissions),
        }
    )
    (store_path / ow.AUDIT / "receipt.sha256").write_text(forged_receipt.content_hash())
    return store, forged_receipt


@STORE_RUNS
def test_store_run_a_forged_resources_applied_reaches_the_probe_and_is_refused_there(
    closed: dict[str, Closed], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, receipt = closed["positive"]
    shutil.copytree(root / "store", tmp_path / "forged")
    store, forged = _forge(tmp_path / "forged", receipt)
    ow._verify_audit(store, forged)  # everything upstream of the probe passes on the copy ...
    reached: list[str] = []

    def spy(executed: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        reached.append(attempt.module_id)
        cp3c.probe(executed, snapshot, attempt)

    monkeypatch.setitem(ow._PROBES, MODULE, spy)
    with pytest.raises(WorkflowError) as caught:  # ... and the CP-3C probe refuses it
        ow.verify_owner_run_receipt(store, forged)
    assert caught.value.code == "identity_mismatch"
    assert reached == [MODULE]


@STORE_RUNS
def test_store_run_an_edited_step_output_is_caught_by_the_blob_hash(
    closed: dict[str, Closed], tmp_path: Path
) -> None:
    root, receipt = closed["positive"]
    shutil.copytree(root / "store", tmp_path / "store")
    store = Execution(tmp_path / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    blob = tmp_path / "store" / "blobs" / (attempt.steps[0].output_sha256 or "")
    blob.write_bytes(blob.read_bytes() + b" ")
    with pytest.raises(WorkflowError) as caught:
        ow.verify_owner_run_receipt(store, receipt)
    assert caught.value.code == "identity_mismatch"
