"""CP-2D acceptance (docs/CP2D-OWNER-LEASE.md: Refusals, Tool use, Acceptance; expected.json
`negative_cases`, `tool_use`, `cp2d_module`).

Two groups. The fast group drives the real `OwnerWorkflow` over the synthetic store of
`test_connect_cp2d` (upstream heads settled by hand, `OwnerWorkflow(store, ("CP-2D",), None)`),
so the read, the refused invoke, the premature submit, the stale binding, the blocked walk and the
refused begin run in seconds. The store-run group needs a real CP-1 promotion (11 to 26 minutes)
and a receipt over the full plan, so it is written here and run only with `CP2D_STORE_RUNS=1`
(Stage 5): the three store runs, the receipt verifier, store bytes unchanged and the tamper
tests.
"""

import hashlib
import importlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as tc
import test_method_cp2d as tm

from deploy_vii.contracts import Input
from deploy_vii.execution import Attempt, Execution, head_of
from deploy_workflow.owner_workflow import BLOCKED_EDGE, OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.owners import cp2d
from deploy_workflow.workflow import WorkflowError

ow: Any = importlib.import_module("deploy_workflow.owner_workflow")
drive: Any = importlib.import_module("cp2d_runs")

# --- the fast group: the real workflow over the synthetic store -------------------------------


def _workflow(root: Path, case: str = "positive") -> tuple[OwnerWorkflow, Execution]:
    store = tc.make_store(root, tc.cp1_module(tm._operands(case)))
    return OwnerWorkflow(store, ("CP-2D",), None), store


def _payload(case: str = "positive") -> str:
    return tc._literal(case)


def test_the_step_is_session_less_and_the_walk_begins_cp2d(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    assert workflow._session is None and workflow._binding.module_id == "CP-2D"
    assert workflow._binding.step_id == "liquidity_bridge" and workflow._spec.inputs != "none"
    pending = [a for a in store.read().attempts if a.status == "pending"]
    assert [a.module_id for a in pending] == ["CP-2D"]


def test_every_invoke_is_a_refused_receipt_and_no_call_is_ok(tmp_path: Path) -> None:
    workflow, _ = _workflow(tmp_path)
    for tool, arguments in (
        ("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}),
        ("search_pack", {"query": "revolving", "source_id": "financial"}),
    ):
        call = workflow.invoke(tool, arguments)
        assert (call["status"], call["error_code"], call["body"]) == (
            "refused",
            "not_permitted",
            None,
        )
    workflow.read_inputs()
    assert workflow.submit_review(_payload())["status"] == "valid"
    assert workflow._calls and all(c.status != "ok" for c in workflow._calls)


def test_submit_before_read_inputs_is_not_permitted(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    before = store.read().content_hash()
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(_payload())
    assert caught.value.code == "not_permitted"
    assert store.read().content_hash() == before  # nothing was journaled


def test_read_inputs_body_is_the_exact_view_and_is_counted(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    record = workflow.read_inputs()
    attempt = next(a for a in store.read().attempts if a.status == "pending")
    digest, body = cp2d.view(store, attempt)
    assert (record["inputs_sha256"], record["body"]) == (digest, body)
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    assert QUOTES.isdisjoint({q for q in QUOTES if q in body})


QUOTES = {tc.QUOTE}


def test_a_snapshot_change_between_read_and_submit_is_stale_binding(tmp_path: Path) -> None:
    workflow, store = _workflow(tmp_path)
    workflow.read_inputs()
    store.interrupt(workflow._binding.ticket_id, "external change between read and submit")
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(_payload())
    assert caught.value.code == "stale_binding"


@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_inputs_are_hash_equal_to_the_final_heads_plus_the_tail(tmp_path: Path, case: str) -> None:
    workflow, store = _workflow(tmp_path, case)
    workflow.read_inputs()
    assert workflow.submit_review(_payload(case))["status"] == "valid"
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    expected = (
        Input(input_id="prepared-pack", sha256=snapshot.pack_sha256),
        *(
            Input(input_id=m, sha256=heads[m].result_sha256, status=heads[m].status)  # type: ignore[arg-type]
            for m in ("CP-0", "CP-1", "CP-2")
        ),
    )
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-2D")
    assert attempt.inputs == expected
    module = store.head_module(heads["CP-2D"])
    tail = cp2d.LiquidityBridgeSubmission.model_validate_json(_payload(case)).content_hash()
    assert module.inputs == (*expected, Input(input_id="liquidity-bridge-submission", sha256=tail))
    assert heads["CP-2D"] == head_of(module, cp2d.QUALIFICATION)


def test_blocked_cp2d_walks_to_a_blocked_head_and_the_reader_has_status_only(
    tmp_path: Path,
) -> None:
    workflow, store = _workflow(tmp_path)
    blocked = tm.SUBMISSIONS["cp2d_blocked"]
    issues = tm.EXPECTED["negative_cases"]["blocked_cp2d"]
    for name in ("attempt_0", "attempt_1"):
        workflow.read_inputs()
        outcome = workflow.submit_review(json.dumps(tm._bind(blocked[name])))
        assert outcome["status"] == "invalid" and outcome["issues"] == issues[name]["issues"]
    assert workflow._phase == "complete"
    head = next(h for h in store.read().heads if h.module_id == "CP-2D")
    assert head.status == "blocked"
    read = cp2d.cp2d_reader(store, head)
    assert (read.status, read.head_sha256) == ("blocked", head.result_sha256)
    assert (read.horizon_months, read.minimum_cash, read.funding_gap, read.wall) == (
        None,
        None,
        None,
        (),
    )
    module = store.head_module(head)
    assert not module.facts and not module.tables and not module.claims


def _blocked_cp2_store(root: Path) -> Execution:
    store = Execution.create(root / "store", tc.PACK)
    for module_id in ("CP-0", "CP-1", "CP-1A"):
        tc._settle(
            store, module_id, tc.cp1_module(tm._base_operands()) if module_id == "CP-1" else None
        )
    for _ in range(2):  # attempt 0 rejected, attempt 1 blocked
        attempt = store.begin("CP-2")
        store.finish(attempt.ticket_id, _empty(store, attempt), lambda _c: ("rule failed",))
    return store


def _empty(store: Execution, attempt: Attempt) -> str:
    run = store.read().run
    from deploy_vii.contracts import Module

    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id="CP-2",
        inputs=attempt.inputs,
        attempt=attempt.number,
    ).model_dump_json()


def test_begin_is_refused_when_cp2_is_blocked_and_no_attempt_is_consumed(tmp_path: Path) -> None:
    store = _blocked_cp2_store(tmp_path)
    assert next(h for h in store.read().heads if h.module_id == "CP-2").status == "blocked"
    workflow = OwnerWorkflow(store, ("CP-2D",), None)
    assert len(workflow._refusals) == 1 and workflow._refusals[0].reason == BLOCKED_EDGE
    assert workflow._refusal_kind == "blocked" and workflow._phase == "complete"
    assert [a for a in store.read().attempts if a.module_id == "CP-2D"] == []
    assert not any(h.module_id == "CP-2D" for h in store.read().heads)


def test_a_stale_required_head_is_not_a_retained_refusal(tmp_path: Path) -> None:
    """Plan note: only the blocked half of the oracle's 'a stale required head refuses the same
    way' is a retained refusal; a stale one re-raises at begin (owner_workflow `_begin`) and
    consumes no attempt."""
    store = tc.make_store(tmp_path, tc.cp1_module(tm._base_operands()))
    store.replace_pack(tc.PACK.model_copy(update={"sources": tc.PACK.sources[:1]}))
    assert {h.status for h in store.read().heads} == {"stale"}
    with pytest.raises(ValueError, match=BLOCKED_EDGE):
        OwnerWorkflow(store, ("CP-2D",), None)
    assert [a for a in store.read().attempts if a.module_id == "CP-2D"] == []


# --- the store-run group (CP-1 promotion; Stage 5) --------------------------------------------

STORE_RUNS = pytest.mark.skipif(
    os.environ.get("CP2D_STORE_RUNS") != "1", reason="needs a real CP-1 promotion (Stage 5)"
)


def _tree(*roots: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file()
    }


@pytest.fixture(scope="module")
def reached(tmp_path_factory: pytest.TempPathFactory) -> tuple[OwnerWorkflow, Path]:
    root = tmp_path_factory.mktemp("cp2d-reached")
    workflow, _ = drive.reach(root)
    return workflow, root


@pytest.fixture(scope="module")
def reached_cp2(tmp_path_factory: pytest.TempPathFactory) -> tuple[OwnerWorkflow, Path]:
    root = tmp_path_factory.mktemp("cp2d-reached-cp2")
    workflow, _ = drive.reach_cp2(root)
    return workflow, root


@pytest.fixture(scope="module")
def closed(
    reached: tuple[OwnerWorkflow, Path], tmp_path_factory: pytest.TempPathFactory
) -> dict[str, tuple[Path, OwnerRunReceipt]]:
    out: dict[str, tuple[Path, OwnerRunReceipt]] = {}
    for case in tm.PACK_CASES:
        root = tmp_path_factory.mktemp(f"cp2d-{case}")
        _store, receipt = drive.cp2d_closed(case, root, reached[0])
        out[case] = (root, OwnerRunReceipt.model_validate_json(receipt.read_bytes()))
    return out


@STORE_RUNS
@pytest.mark.parametrize("case", tm.PACK_CASES)
def test_store_run_inputs_heads_receipt_and_unchanged_bytes(
    closed: dict[str, tuple[Path, OwnerRunReceipt]], case: str
) -> None:
    root, receipt = closed[case]
    store = Execution(root / "store")
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-2D")
    expected = (
        Input(input_id="prepared-pack", sha256=snapshot.pack_sha256),
        *(
            Input(input_id=m, sha256=heads[m].result_sha256, status=heads[m].status)  # type: ignore[arg-type]
            for m in ("CP-0", "CP-1", "CP-2")
        ),
    )
    assert attempt.inputs == expected
    module = store.head_module(heads["CP-2D"])
    assert module.inputs[:-1] == expected and module.inputs[-1].input_id == (
        "liquidity-bridge-submission"
    )
    assert heads["CP-2D"].status == tm.CASES[case]["status"]
    assert (
        list(module.limitations)[: len(tm.CASES[case]["own_limitations"])]
        == (tm.CASES[case]["own_limitations"])
    )
    before = _tree(root / "store")
    drive.verify_receipt(root / "store", receipt)
    assert _tree(root / "store") == before
    assert [c for c in receipt.calls if c.binding.module_id == "CP-2D" and c.status == "ok"] == []
    reads = [r for r in receipt.input_reads if r.binding.module_id == "CP-2D"]
    assert (
        len(reads) == 1
        and reads[0].inputs_sha256 == hashlib.sha256(reads[0].body.encode()).hexdigest()
    )


@STORE_RUNS
def test_store_run_read_body_matches_the_frozen_tree_and_has_no_quote(
    closed: dict[str, tuple[Path, OwnerRunReceipt]],
) -> None:
    _, receipt = closed["positive"]
    body = json.loads(next(r for r in receipt.input_reads if r.binding.module_id == "CP-2D").body)
    assert list(body) == tm.MANIFEST["view_tree_draft"]["top_level_keys_in_order"]
    assert not set(tm.MANIFEST["view_tree_draft"]["forbidden_keys"]) & set(tc._keys(body))


@STORE_RUNS
def test_store_run_submit_before_read_and_stale_binding(
    reached: tuple[OwnerWorkflow, Path], tmp_path: Path
) -> None:
    workflow = drive.s1a.clone_workflow(reached[0], tmp_path)
    with pytest.raises(WorkflowError) as early:
        workflow.submit_review(drive.literal("positive", workflow))
    assert early.value.code == "not_permitted"
    workflow.read_inputs()
    Execution(tmp_path / "store").interrupt(workflow._binding.ticket_id, "external change")
    with pytest.raises(WorkflowError) as stale:
        workflow.submit_review(drive.literal("positive", workflow))
    assert stale.value.code == "stale_binding"


@STORE_RUNS
def test_store_run_blocked_cp2d_has_a_verifying_receipt_and_a_status_only_reader(
    reached: tuple[OwnerWorkflow, Path], tmp_path: Path
) -> None:
    workflow = drive.blocked_cp2d(tmp_path, reached[0])
    receipt_path = drive.seal(workflow, tmp_path)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_bytes())
    drive.verify_receipt(tmp_path / "store", receipt)
    store = Execution(tmp_path / "store")
    head = next(h for h in store.read().heads if h.module_id == "CP-2D")
    read = cp2d.cp2d_reader(store, head)
    assert read.status == "blocked" and read.wall == () and read.funding_gap is None


@STORE_RUNS
def test_store_run_begin_refused_cp2_blocked_consumes_no_attempt(
    reached_cp2: tuple[OwnerWorkflow, Path], tmp_path: Path
) -> None:
    workflow = drive.begin_refused_cp2_blocked(tmp_path, reached_cp2[0])
    receipt = OwnerRunReceipt.model_validate_json(drive.seal(workflow, tmp_path).read_bytes())
    drive.verify_receipt(tmp_path / "store", receipt)
    store = Execution(tmp_path / "store")
    assert [a for a in store.read().attempts if a.module_id == "CP-2D"] == []
    assert len(receipt.refusals) == 1 and receipt.refusals[0].reason == BLOCKED_EDGE
    assert not any(h.module_id == "CP-2D" for h in store.read().heads)


@STORE_RUNS
def test_store_run_tamper_passes_audit_then_the_verifier_refuses(
    closed: dict[str, tuple[Path, OwnerRunReceipt]], tmp_path: Path
) -> None:
    src_root, receipt = closed["positive"]
    shutil.copytree(src_root / "store", tmp_path / "store")
    store = Execution(tmp_path / "store")

    def refuses(forged: OwnerRunReceipt = receipt) -> None:
        with pytest.raises(WorkflowError) as caught:
            drive.verify_receipt(tmp_path / "store", forged)
        assert caught.value.code == "identity_mismatch"

    drive.verify_receipt(tmp_path / "store", receipt)
    # a consistent forged read body: audit file, receipt copy and seal agree, the view replay refuses
    reads = tmp_path / "store/owner-run-audit/input-reads"
    old = next(r for r in receipt.input_reads if r.binding.module_id == "CP-2D")
    body = old.body.replace("cp1_facts_note", "cp1_facts_notX", 1)
    edited = old.model_copy(
        update={"body": body, "inputs_sha256": hashlib.sha256(body.encode()).hexdigest()}
    )
    forged = receipt.model_copy(
        update={"input_reads": tuple(edited if r == old else r for r in receipt.input_reads)}
    )
    (reads / old.content_hash()).unlink()
    (reads / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    sealed = tmp_path / "store/owner-run-audit/receipt.sha256"
    sealed.write_text(forged.content_hash())
    ow._verify_audit(store, forged)  # the audit and the seal agree with the forged copy
    with pytest.raises(WorkflowError) as replay:
        ow._verify_calls_reads(store, forged, ow.OWNER_SPECS)
    assert replay.value.code == "identity_mismatch"
    refuses(forged)
    (reads / edited.content_hash()).unlink()
    (reads / old.content_hash()).write_bytes(old.model_dump_json().encode())
    sealed.write_text(receipt.content_hash())
    drive.verify_receipt(tmp_path / "store", receipt)

    # an edited step output: the store's own blob hash check refuses it
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-2D")
    blob = tmp_path / "store/blobs" / (attempt.steps[0].output_sha256 or "")
    original = blob.read_bytes()
    blob.write_bytes(original + b" ")
    refuses()
    blob.write_bytes(original)
    drive.verify_receipt(tmp_path / "store", receipt)

    # an edited SettledHead
    heads = tuple(
        h.model_copy(update={"status": "accepted"}) if h.module_id == "CP-2D" else h
        for h in receipt.heads
    )
    refuses(receipt.model_copy(update={"heads": heads}))
    wrong = tuple(
        h.model_copy(update={"result_sha256": "0" * 64}) if h.module_id == "CP-2D" else h
        for h in receipt.heads
    )
    refuses(receipt.model_copy(update={"heads": wrong}))


@STORE_RUNS
def test_store_run_reader_on_the_closed_head(
    closed: dict[str, tuple[Path, OwnerRunReceipt]],
) -> None:
    for case, (root, _) in closed.items():
        store = Execution(root / "store")
        head = next(h for h in store.read().heads if h.module_id == "CP-2D")
        read = cp2d.cp2d_reader(store, head)
        want = tm.CASES[case]
        assert (
            read.horizon_months == want["horizon_months"] and read.head_sha256 == head.result_sha256
        )
        assert read.status == head.status and len(read.wall) == len(want["tables"]["T2E.4"]["rows"])
        assert (read.minimum_cash is None) == (want["minimum_cash"] is None)
