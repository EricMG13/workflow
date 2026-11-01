"""A refused begin is recorded with its missing inputs and the owner walk continues (Part B O3+O4
Task 1, G3).

Before this change a refusal (`NotAuthorized`, or the blocked-edge `ValueError`) ended the walk and
every later module was skipped. Now `_begin` records the refusal and calls `_advance`, so the next
module is begun (or the CP-MODEL stop is reached, or the plan ends). Every module planned is
exactly one of settled or refused; `_verify_walk` checks that against the journal.

The registry-backed claims run on the real `dependencies` over hand-built snapshots
(`test_missing_inputs_*`: the `distressed_restructuring` preset has no frozen CP-0, B21). The walk
tests use the real store with the G1-X fake module (`CP-3D`) and `CP-1C`, which blocks on a
blocked CP-1 (four empty submissions, about 0.5 s). The CP-0 payloads edited here are TEST INPUT,
not oracle (as `s1a_runs.cp0_cp1a_conditional`). A module planned after CP-5 refused by command
needs CP-5 settled (slow): that test is behind RUN_PROMOTION.
"""

import importlib
import json
import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from deploy_vii.contracts import Run
from deploy_vii.execution import (
    Command,
    ExecutionSnapshot,
    Head,
    NotAuthorized,
    current_inputs,
)
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
g1x: Any = importlib.import_module("test_owner_g1x")
order_tests: Any = importlib.import_module("test_owner_order")
financial: Any = importlib.import_module("test_financial_workflow")
cp3 = order_tests.cp3  # the fixture: the G1-X fake registered as CP-3 / CP-3D

A = g1x.MODULE  # CP-3D: needs only CP-0
B = "CP-1C"  # needs CP-0 and CP-1: refused (blocked edge) while CP-1 is blocked
ZERO = "0" * 64


@pytest.fixture
def fake(cp3: SimpleNamespace) -> Iterator[SimpleNamespace]:
    yield cp3


def _review(pack: Any, *conditional: str) -> str:
    """CP-0 with a READY row per fake module and CP-1C; `conditional` rows are CONDITIONAL, so
    their T8 command is "DO NOT RUN" (CP-0 does not authorise them). Test input, not oracle."""
    review = json.loads(order_tests._readiness_commanding_module(pack, B))
    for row in review["consumers"]:
        if row["module_id"] in conditional:
            row["readiness"] = "CONDITIONAL"
            row["missing_source"] = "financial: test input, source not located"
            row["rationale"] = "Test input: this consumer is not authorised in this CP-0."
    return json.dumps(review)


def _walk(fake: SimpleNamespace, root: Path, order: tuple[str, ...], *conditional: str) -> Any:
    """CP-0 valid, CP-1 blocked, then the walk continues through `order`."""
    fake.monkeypatch.setattr(owner, "plan", lambda requested: order)
    pack = order_tests._financial_pack(B)
    workflow = owner.OwnerWorkflow.create(
        root / "store", pack, specs=owner.OWNER_SPECS, publication_directory=root / "model"
    )
    financial.read_sources(workflow)
    assert workflow.submit_review(_review(pack, *conditional))["status"] == "valid"
    for _ in range(4):
        for source in ("identity", "financial"):
            call = workflow.invoke(
                "read_pages", {"source_id": source, "first_page": 1, "last_page": 1}
            )
            assert call["status"] == "ok"
        search = {"query": "subsequent", "source_id": "financial"}
        assert workflow.invoke("search_pack", search)["status"] == "ok"
        assert workflow.submit_review("{}")["status"] == "invalid"
    return workflow


ORDER = ("CP-0", "CP-1", B, A)


def _completed(fake: SimpleNamespace, root: Path) -> Any:
    """CP-1C is refused by the blocked CP-1, then the fake module A begins and settles."""
    workflow = _walk(fake, root, ORDER)
    assert [r.module_id for r in workflow._refusals] == [B]
    assert workflow._binding.module_id == A  # the walk continued past the refusal
    g1x._drive(workflow)
    assert workflow.phase == "complete"
    return workflow


def _verdict(root: Path, receipt: Any) -> str:
    return str(g1x._verdict(root, receipt))


# --- the contract field -------------------------------------------------------------------------


def test_refused_begin_omits_empty_missing_fields_and_bounds_them() -> None:
    plain = owner.RefusedBegin(module_id="CP-4", snapshot_sha256=ZERO, reason="r")
    assert "missing_inputs" not in json.loads(plain.model_dump_json())
    assert "missing_commands" not in json.loads(plain.model_dump_json())
    full = owner.RefusedBegin(
        module_id="CP-4C",
        snapshot_sha256=ZERO,
        reason="r",
        missing_inputs=("CP-4",),
        missing_commands=("Run CP-4C",),
    )
    body = json.loads(full.model_dump_json())
    assert body["missing_inputs"] == ["CP-4"] and body["missing_commands"] == ["Run CP-4C"]
    with pytest.raises(ValidationError):
        owner.RefusedBegin(
            module_id="CP-4", snapshot_sha256=ZERO, reason="r", missing_commands=("x" * 161,)
        )
    with pytest.raises(ValidationError):  # Identifier rejects a space (ruling F7)
        owner.RefusedBegin(
            module_id="CP-4", snapshot_sha256=ZERO, reason="r", missing_inputs=("Run CP-4",)
        )


# --- _missing_inputs over the real dependencies (hand-built snapshots) --------------------------

DISTRESSED = ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-2A", "CP-2G", "CP-2H", "CP-4", "CP-4C", "CP-5")


def _snapshot(settled: tuple[str, ...], runnable: tuple[str, ...]) -> ExecutionSnapshot:
    """`settled` modules have an accepted head; CP-0's commands authorise `runnable`."""
    run = Run(
        run_id="refusals-test",
        issuer_id="issuer",
        issuer_name="Issuer",
        as_of=date(2026, 1, 10),
        case_kind="synthetic",
        pathway="distressed_restructuring",
    )
    commands = tuple(Command(row_id=m, text=f"Run {m}") for m in runnable)
    heads = tuple(
        Head(
            module_id=m,
            status="accepted",
            result_sha256=ZERO,
            inputs=(),
            commands=commands if m == "CP-0" else (),
        )
        for m in settled
    )
    return ExecutionSnapshot(run=run, pack_sha256=ZERO, heads=heads)


def _error(snapshot: ExecutionSnapshot, module: str) -> ValueError:
    with pytest.raises(ValueError) as caught:
        current_inputs(snapshot, module)
    return caught.value


def test_missing_inputs_chain_on_the_real_dependencies() -> None:
    """CP-4 is not authorised (no `Run CP-4`); CP-2G/CP-2H can begin; CP-4C is refused for the
    missing CP-4; CP-5 for CP-4 and CP-4C, in plan order. CP-5 does not settle over them:
    settling needs execution.py:244-246, outside B1 (user question Q1)."""
    runnable = ("CP-1", "CP-1A", "CP-2", "CP-2A", "CP-2G", "CP-2H", "CP-4C", "CP-5")
    settled = ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-2A", "CP-2G", "CP-2H")
    before = _snapshot(settled, runnable)
    error = _error(before, "CP-4")
    assert isinstance(error, NotAuthorized)
    assert owner._missing_inputs(before, "CP-4", error) == ((), ("Run CP-4",))

    after = before
    for module in ("CP-2G", "CP-2H"):
        current_inputs(after, module)  # can begin
    error = _error(after, "CP-4C")
    assert not isinstance(error, NotAuthorized)
    assert str(error).startswith(owner.BLOCKED_EDGE)
    assert owner._missing_inputs(after, "CP-4C", error) == (("CP-4",), ())
    error = _error(after, "CP-5")
    assert owner._missing_inputs(after, "CP-5", error) == (("CP-4", "CP-4C"), ())


def test_missing_inputs_names_a_blocked_producer_without_a_restricted_edge() -> None:
    """A blocked head under a `block` edge is unusable, so it is named too."""
    snapshot = _snapshot(("CP-0", "CP-1", "CP-1A"), ("CP-2",))
    heads = tuple(
        h.model_copy(update={"status": "blocked"}) if h.module_id == "CP-1" else h
        for h in snapshot.heads
    )
    blocked = snapshot.model_copy(update={"heads": heads})
    error = _error(blocked, "CP-2")
    assert owner._missing_inputs(blocked, "CP-2", error) == (("CP-1",), ())


# --- the walk continues -------------------------------------------------------------------------


def test_walk_continues_past_a_refusal_and_verifies(fake: SimpleNamespace, tmp_path: Path) -> None:
    workflow = _completed(fake, tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    refusal = receipt.refusals[0]
    assert refusal.module_id == B and refusal.reason.startswith(owner.BLOCKED_EDGE)
    assert refusal.missing_inputs == ("CP-1",) and refusal.missing_commands == ()
    assert [b.module_id for b in receipt.begins][-1] == A  # A began after the refusal
    assert _verdict(tmp_path, receipt) == "accepted"  # reason == BLOCKED_EDGE verifies


def test_refusal_does_not_skip_cp_model_stop(fake: SimpleNamespace, tmp_path: Path) -> None:
    """With a refusal before the CP-MODEL position the walk stops at CP-MODEL, `publish` runs and
    the later module resumes (F3: `_advance`, not a direct skip to the next analytical)."""
    order = ("CP-0", "CP-1", B, "CP-MODEL", A)
    workflow = _walk(fake, tmp_path, order)
    assert [r.module_id for r in workflow._refusals] == [B]
    assert workflow.phase == "walked" and workflow._resume_after == "CP-MODEL"
    assert A not in {a.module_id for a in workflow._store.read().attempts}
    assert workflow.publish()["status"] == "refused"  # CP-1 is blocked: terminal
    assert workflow.phase == "analytical" and workflow._binding.module_id == A
    g1x._drive(workflow)
    assert workflow.phase == "complete"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert receipt.refusals[0].snapshot_sha256 == receipt.publications[0].snapshot_before_sha256
    assert _verdict(tmp_path, receipt) == "accepted"


def test_first_refusal_kind_is_kept(fake: SimpleNamespace, tmp_path: Path) -> None:
    """A is not authorised (not_authorized), then B is refused by the blocked CP-1 (blocked):
    `_refusal_code` still names the first (L2)."""
    workflow = _walk(fake, tmp_path, ("CP-0", "CP-1", A, B), A)
    assert [r.module_id for r in workflow._refusals] == [A, B]
    assert workflow._refusals[0].missing_commands == (f"Run {A}",)
    assert workflow._refusals[0].missing_inputs == ()
    assert workflow._refusals[1].missing_inputs == ("CP-1",)
    assert workflow._refusal_kind == "not_authorized"
    assert workflow._refusal_code() == f"{A.lower().replace('-', '')}_not_authorized"
    assert workflow.phase == "complete"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    # consecutive refusals share one snapshot: a refusal does not change the journal
    assert receipt.refusals[0].snapshot_sha256 == receipt.refusals[1].snapshot_sha256
    assert _verdict(tmp_path, receipt) == "accepted"


def test_unrelated_value_error_still_propagates(fake: SimpleNamespace, tmp_path: Path) -> None:
    real = owner.Execution.begin

    def begin(self: Any, module_id: str, *args: Any, **kwargs: Any) -> Any:
        if module_id == B:
            raise ValueError("disk full")
        return real(self, module_id, *args, **kwargs)

    fake.monkeypatch.setattr(owner.Execution, "begin", begin)
    with pytest.raises(ValueError, match="disk full"):
        _walk(fake, tmp_path, ORDER)
    store = owner.Execution(tmp_path / "store")
    audit = store.directory / owner.AUDIT / "refused-begin"
    assert not audit.exists() or not list(audit.iterdir())  # nothing relabelled as a refusal


# --- the verifier -------------------------------------------------------------------------------


def _rejects(root: Path, receipt: Any, planned: tuple[str, ...] = ORDER) -> None:
    store = owner.Execution(root / "store")
    analytical = tuple(m for m in planned if m not in ("CP-MODEL",))
    with pytest.raises(WorkflowError) as caught:
        owner._verify_walk(store, receipt, analytical, planned, None)
    assert caught.value.code == "identity_mismatch"


def test_verifier_accepts_the_real_receipt_and_rejects_forgeries(
    fake: SimpleNamespace, tmp_path: Path
) -> None:
    workflow = _completed(fake, tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = owner.Execution(tmp_path / "store")
    analytical = ("CP-0", "CP-1", B, A)
    owner._verify_walk(store, receipt, analytical, ORDER, None)  # the real receipt passes
    refusal = receipt.refusals[0]

    # (a) the B refusal and head both omitted: skipped though it could not begin
    _rejects(tmp_path, receipt.model_copy(update={"refusals": ()}))
    # (c) the recorded missing inputs / commands edited
    for update in ({"missing_inputs": ("CP-1A",)}, {"missing_commands": ("Run CP-1C",)}):
        forged = refusal.model_copy(update=update)
        _rejects(tmp_path, receipt.model_copy(update={"refusals": (forged,)}))
    # (d) a snapshot taken after A settled, when the refusal was recorded before it
    final = store.read().content_hash()
    assert final != refusal.snapshot_sha256
    late = refusal.model_copy(update={"snapshot_sha256": final})
    _rejects(tmp_path, receipt.model_copy(update={"refusals": (late,)}))
    # (e) two refusals for the same module
    _rejects(tmp_path, receipt.model_copy(update={"refusals": (refusal, refusal)}))
    # (b) a refusal for A, which settled: both a head and a refusal
    wrong = refusal.model_copy(update={"module_id": A})
    _rejects(tmp_path, receipt.model_copy(update={"refusals": (refusal, wrong)}))


def test_verifier_rejects_a_refusal_for_a_module_that_could_begin(
    fake: SimpleNamespace, tmp_path: Path
) -> None:
    """A could begin at the snapshot before it began: `_verify_refusal` refuses the claim."""
    workflow = _completed(fake, tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = owner.Execution(tmp_path / "store")
    begin = next(b for b in receipt.begins if b.module_id == A)
    claim = owner.RefusedBegin(
        module_id=A, snapshot_sha256=begin.snapshot_before_sha256, reason="CP-0 has not authorized"
    )
    with pytest.raises(WorkflowError) as caught:
        owner._verify_refusal(owner._snapshot(store, claim.snapshot_sha256), claim, {B})
    assert caught.value.code == "identity_mismatch"


def test_the_old_no_continue_receipt_is_rejected(fake: SimpleNamespace, tmp_path: Path) -> None:
    """`_advance` stopping after a refusal leaves A, planned after it, unbegun: neither settled
    nor refused, so the receipt is rejected (f)."""
    real = owner.OwnerWorkflow._advance

    def stop_after_refusal(self: Any, module_id: str) -> None:
        if self._refusals:
            self._finish_walk()
        else:
            real(self, module_id)

    fake.monkeypatch.setattr(owner.OwnerWorkflow, "_advance", stop_after_refusal)
    workflow = _walk(fake, tmp_path, ORDER)
    assert workflow.phase == "complete" and A not in {
        a.module_id for a in workflow._store.read().attempts
    }
    with pytest.raises(WorkflowError) as caught:
        workflow.write_receipt(tmp_path / "receipt.json")
    assert caught.value.code == "identity_mismatch"


def test_a_faults_file_next_to_the_audit_kinds_does_not_break_the_audit(
    fake: SimpleNamespace, tmp_path: Path
) -> None:
    """Pin (not RED): `_verify_audit` lists seven compared kinds and ignores a `faults/` entry."""
    workflow = _completed(fake, tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = owner.Execution(tmp_path / "store")
    faults = store.directory / owner.AUDIT / "faults"
    faults.mkdir()
    (faults / "x").write_text("{}")
    assert _verdict(tmp_path, receipt) == "accepted"


# --- deferred: needs CP-5 settled (slow) ---------------------------------------------------------

promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1",
    reason="full o2 walk to CP-8 (CP-1 105 s, publish 72 s): over 5 minutes (B16); deferred",
)


@promotion
def test_module_planned_after_cp5_refused_cp5_still_settles(tmp_path: Path) -> None:
    """The frozen o2 case: CP-0 does not authorise CP-8 (planned after CP-5). CP-5 settles, then
    CP-8 is refused with its missing command and the receipt verifies."""
    o2_case: Any = importlib.import_module("o2_case")
    authored = o2_case.author(tmp_path, answers=o2_case.ALL_STEPS)
    run_dir = authored.run_dir
    receipt = owner.OwnerRunReceipt.model_validate_json((run_dir / "owner-run.json").read_text())
    store = owner.Execution(run_dir / "execution")
    owner.verify_owner_run_receipt(store, receipt, publication_directory=run_dir / "publication")
    assert [r.module_id for r in receipt.refusals] == ["CP-8"]
    assert receipt.refusals[0].missing_commands == ("Run CP-8",)
    assert "CP-5" in {h.module_id for h in receipt.heads}


def test_o2_synthetic_walk_with_cp1_unauthorised(tmp_path: Path) -> None:
    """The frozen o2 CP-0 with CP-1 made CONDITIONAL (its `Run CP-1` command gone; TEST INPUT,
    not oracle, labelled as `s1a_runs.cp0_cp1a_conditional`). Measured, not assumed: CP-1 is
    refused by command; CP-1A needs only CP-0 so it begins and settles (frozen payload); every
    other module is refused with its missing inputs, in plan order; CP-MODEL is refused
    terminally (no CP-1 head); the receipt verifies."""
    o2_case: Any = importlib.import_module("o2_case")
    (tmp_path / "recordings").mkdir()
    adapter = importlib.import_module("deploy_workflow.model.adapter")
    _, run_dir = o2_case._prepare(
        tmp_path / "prepared", adapter.recorded_adapter(o2_case.MODEL, tmp_path / "recordings")
    )
    pack = importlib.import_module("deploy_vii.preparation").load_pack(run_dir / "pack")
    workflow = owner.OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    document = json.loads(o2_case.payload_for("source_readiness"))
    row = next(c for c in document["consumers"] if c["module_id"] == "CP-1")
    row["readiness"] = "CONDITIONAL"
    row["missing_source"] = "financial: restated statements"
    row["rationale"] = "Test input: the restated statements are not yet located."
    assert workflow.submit_review(json.dumps(document))["status"] == "valid"
    assert workflow.binding.module_id == "CP-1A"  # CP-1 refused, the walk went on
    source, query = o2_case.BUSINESS_SEARCH
    assert workflow.invoke("search_pack", {"query": query, "source_id": source})["status"] == "ok"
    assert workflow.submit_review(o2_case.payload_for("business_context"))["status"] == "valid"
    assert workflow.phase == "walked" and workflow._resume_after == "CP-MODEL"
    assert workflow.publish()["status"] == "refused"  # CP-1 has no head: terminal
    assert workflow.phase == "complete"
    seen = [(r.module_id, r.missing_inputs, r.missing_commands) for r in workflow._refusals]
    assert seen == [
        ("CP-1", (), ("Run CP-1",)),
        ("CP-2", ("CP-1",), ()),
        ("CP-3", ("CP-1", "CP-2"), ()),
        ("CP-5", ("CP-1", "CP-2", "CP-3"), ()),
        ("CP-6", ("CP-1", "CP-2", "CP-3", "CP-5"), ()),
        ("CP-8", ("CP-6",), ()),
    ]
    assert all(r.reason.startswith(owner.BLOCKED_EDGE) for r in workflow._refusals[1:])
    assert workflow._refusal_code() == "cp1_not_authorized"  # the first refusal
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(owner.Execution(tmp_path / "store"), receipt)
    assert [h.module_id for h in receipt.heads] == ["CP-0", "CP-1A"]
    assert len(receipt.publications) == 1
