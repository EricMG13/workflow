"""CP-1D store acceptance (docs/CP1D-OWNER-LEASE.md Acceptance A1-A5): deferred to Stage 5.

Every closed run promotes CP-1 for real (11-26 minutes per case, module-scoped fixtures, one job
under the lock). Written, not run, in Stage 2: the fast connection checks are in
`tests/test_connect_cp1d.py`. Expectations come only from `cases/cp1d-owner/*.json`. Fixtures vary
the case (statuses, as-of pack, staleness) so a constant equal to one oracle value cannot pass.

Command: `PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_owner_cp1d.py`.
"""

import hashlib
import importlib
import json
import re
import shutil
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import Module
from deploy_vii.execution import Attempt, Execution
from deploy_vii.live.tools import cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import (
    OWNER_SPECS,
    OwnerRunReceipt,
    OwnerWorkflow,
    _verify_audit,
    _verify_calls_reads,
    verify_owner_run_receipt,
)
from deploy_workflow.owners import cp1d
from deploy_workflow.workflow import WorkflowError

runs: Any = importlib.import_module("cp1d_runs")
ORACLE: dict[str, Any] = runs.oracle()
EXPECTED: dict[str, Any] = ORACLE["expected"]
SUBMISSIONS: dict[str, Any] = ORACLE["submissions"]
CASES = runs.CASES
FORBIDDEN_KEYS = {"quote", "citations", "record_json"}


# --- helpers ---------------------------------------------------------------------------------


def _verify(root: Path, receipt: Any) -> None:
    verify_owner_run_receipt(Execution(root / "store"), receipt)


def _tree(*roots: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file()
    }


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _module(store: Execution, module_id: str) -> Module:
    return store.head_module(_head(store, module_id))


def _attempts(store: Execution, module_id: str) -> list[Attempt]:
    return [a for a in store.read().attempts if a.module_id == module_id]


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


@dataclass
class Closed:
    case: str
    root: Path
    store: Execution
    pack: PreparedPack
    receipt: OwnerRunReceipt
    expected: dict[str, Any]


_PROMOTED: dict[str, tuple[OwnerWorkflow, PreparedPack]] = {}


def _promoted(case: str, factory: pytest.TempPathFactory) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled once per case (the slow part); CP-1D begun, untouched."""
    if case not in _PROMOTED:
        _PROMOTED[case] = runs.promoted(case, factory.mktemp(f"cp1d-promoted-{case}"))
    return _PROMOTED[case]


def _fork(promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path) -> OwnerWorkflow:
    return runs.S1A.clone_workflow(promoted[0], tmp_path)  # type: ignore[no-any-return]


@pytest.fixture(scope="module", params=CASES)
def closed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    case: str = request.param
    template, pack = _promoted(case, tmp_path_factory)
    root = tmp_path_factory.mktemp(f"cp1d-closed-{case}")
    workflow = runs.S1A.clone_workflow(template, root)
    runs.close(workflow, case, root / "owner-receipt.json")
    receipt = OwnerRunReceipt.model_validate_json((root / "owner-receipt.json").read_bytes())
    return Closed(case, root, Execution(root / "store"), pack, receipt, EXPECTED["cases"][case])


@pytest.fixture(scope="module")
def positive_promoted(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[OwnerWorkflow, PreparedPack]:
    return _promoted("positive", tmp_path_factory)


# --- A1/A1b/A2: the closed runs ---------------------------------------------------------------


def test_plan_heads_and_statuses(closed: Closed) -> None:
    assert closed.receipt.plan == tuple(ORACLE["manifest"]["plan"]["plan_order"])
    heads = {h.module_id: h.status for h in closed.store.read().heads}
    assert set(heads) == {"CP-0", "CP-1", "CP-1D"}
    assert heads["CP-1D"] == closed.expected["module_status"]
    (attempt,) = _attempts(closed.store, "CP-1D")
    assert attempt.number == 0 and attempt.status == "finished" and not attempt.issues


def test_facts_tables_claims_and_limitations_equal_the_oracle(closed: Closed) -> None:
    module = _module(closed.store, "CP-1D")
    want = closed.expected
    by_id = {f.fact_id: f for f in module.facts}
    for fact in want["facts"]:
        raw = fact.get("amount_exact")
        mine = by_id[fact["fact_id"]]
        assert mine.amount == (None if raw is None else Decimal(raw)), fact["fact_id"]
        assert mine.status == fact["status"], fact["fact_id"]
    assert {f.fact_id for f in module.facts if f.table_id.startswith("T1D.")} == {
        f["fact_id"] for f in want["facts"]
    }
    assert [t.table_id for t in module.tables][:7] == [t["table_id"] for t in want["tables"]]
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in want["claims"]]
    assert list(module.limitations) == want["settled_limitations"]
    refs = [f for f in module.facts if f.table_id == "cp1_references"]
    assert [f.row_id for f in refs] == [r["row_id"] for r in want["cp1_references"]]


def test_view_body_is_the_lease_key_tree(closed: Closed) -> None:
    read = next(r for r in closed.receipt.input_reads if r.binding.module_id == "CP-1D")
    body = json.loads(read.body)
    assert set(body) == {
        "upstream",
        "bridge",
        "cp1_facts",
        "cp1_t417_rows",
        "cp1_facts_note",
        "inherited_limitations",
    }
    assert not FORBIDDEN_KEYS & _keys(body)
    assert [u["module_id"] for u in body["upstream"]] == ["CP-0", "CP-1"]
    assert (body["bridge"]["state"] == "absent") == (closed.case == "statements_only")


def test_tool_use_per_oracle(closed: Closed) -> None:
    receipt = closed.receipt
    submission = next(
        s
        for s in receipt.submissions
        if s.binding.binding.module_id == "CP-1D" and s.disposition == "valid"
    )
    binding = submission.binding.binding
    reads = [r for r in receipt.input_reads if r.binding == binding]
    assert len(reads) == 1  # exactly one ok read_inputs before the submit
    pages = {
        (c.arguments["source_id"], f"page:{c.arguments['first_page']}")
        for c in receipt.calls
        if c.binding == binding and c.tool == "read_pages" and c.status == "ok"
    }
    cited = {
        (s, loc)
        for s, loc in cited_locators(runs.literal(closed.case, "earnings_quality"))
        if re.fullmatch(r"page:\d+", loc)
    }
    assert cited <= pages
    literal = SUBMISSIONS[closed.case]["tool_calls"]
    assert pages == {
        (c["arguments"]["source_id"], f"page:{c['arguments']['first_page']}")
        for c in literal
        if c["tool"] == "read_pages"
    }
    assert not [c for c in receipt.calls if c.binding == binding and c.status == "refused"]


def test_receipt_verifies_and_the_store_bytes_are_unchanged(closed: Closed) -> None:
    before = _tree(closed.root / "store")
    _verify(closed.root, closed.receipt)
    assert _tree(closed.root / "store") == before


def test_cp1d_confidence_is_never_high(closed: Closed) -> None:
    submitted = json.loads(runs.literal(closed.case, "earnings_quality"))
    assert submitted["overall"]["confidence"] != "High"


def test_downstream_consumption_stays_open_and_no_reader_exists(closed: Closed) -> None:
    """D3: no consumer core reads the head (the lease names no reader); the run only proves the
    head is settled and bindable as `Input("CP-1D", head.result_sha256, status)`."""
    assert not hasattr(cp1d, "cp1d_reader")
    head = _head(closed.store, "CP-1D")
    assert head.status in ("accepted", "restricted")
    assert closed.store.head_module(head).content_hash() == head.result_sha256
    assert EXPECTED["execution"]["consumption"]["status"].startswith("open")


# --- A3 refusals and tool-use refusals (forks of the positive run) ------------------------------


def test_non_pack_tool_is_refused_and_consumes_no_attempt(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(positive_promoted, tmp_path)
    refusal = next(t for t in EXPECTED["tool_refusals"] if t["id"] == "t02")
    call = workflow.invoke(refusal["call"]["tool"], refusal["call"]["arguments"])
    assert (call["status"], call["error_code"]) == ("refused", "not_permitted")
    store = Execution(tmp_path / "store")
    attempt = _attempts(store, "CP-1D")[0]
    assert attempt.steps == () and attempt.status == "pending"


def test_submit_before_read_inputs_is_not_permitted_and_writes_nothing(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(positive_promoted, tmp_path)
    store = Execution(tmp_path / "store")
    before = _tree(tmp_path / "store")
    with pytest.raises(WorkflowError) as unread:
        workflow.submit_review(runs.literal("positive", "earnings_quality"))
    assert unread.value.code == "not_permitted"
    assert _tree(tmp_path / "store") == before
    assert not [s for s in workflow._submissions if s.binding.binding.module_id == "CP-1D"]
    assert _attempts(store, "CP-1D")[0].steps == ()


def test_unread_cited_page_is_an_invalid_attempt_then_repaired(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(positive_promoted, tmp_path)
    body = runs.read_view(workflow)
    outcome = runs.drive_cp1d(workflow, "positive", body)  # no read_pages: attempt 0 is invalid
    refusal = next(t for t in EXPECTED["tool_refusals"] if t["id"] == "t01")
    assert outcome["status"] == "invalid" and outcome["issues"] == refusal["expected_issues"]
    attempts = _attempts(Execution(tmp_path / "store"), "CP-1D")
    assert [a.number for a in attempts] == [0, 1] and attempts[1].repair_of == attempts[0].ticket_id
    body = runs.read_view(workflow)
    runs.tool_calls(workflow, "positive")
    assert runs.drive_cp1d(workflow, "positive", body)["status"] == "valid"
    workflow.write_receipt(tmp_path / "owner-receipt.json")
    receipt = OwnerRunReceipt.model_validate_json((tmp_path / "owner-receipt.json").read_bytes())
    _verify(tmp_path, receipt)


def test_snapshot_change_between_read_and_submit_is_stale_binding(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(positive_promoted, tmp_path)
    body = runs.read_view(workflow)
    runs.tool_calls(workflow, "positive")
    Execution(tmp_path / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    with pytest.raises(WorkflowError) as caught:
        runs.drive_cp1d(workflow, "positive", body)
    assert caught.value.code == "stale_binding"


def test_blocked_after_two_invalid_attempts_has_limitations_only(
    positive_promoted: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    """r06 twice: attempt 0 rejected, attempt 1 blocked; a receipt and the status-only view of
    the blocked head verify, and the head carries no tables."""
    workflow = _fork(positive_promoted, tmp_path)
    literal = next(r for r in SUBMISSIONS["refusals"] if r["id"] == "r06")
    text = json.dumps(literal["payload"])
    for _ in range(2):
        body = runs.read_view(workflow)
        runs.tool_calls(workflow, "positive")
        outcome = runs.drive_cp1d(workflow, "positive", body, text=text)
        assert outcome["status"] == "invalid"
    store = Execution(tmp_path / "store")
    assert _head(store, "CP-1D").status == EXPECTED["blocked"]["head_status"]
    blocked = _module(store, "CP-1D")
    assert blocked.tables == () and blocked.facts == ()
    assert EXPECTED["blocked"]["limitations_contain"] in blocked.limitations
    workflow.write_receipt(tmp_path / "owner-receipt.json")
    receipt = OwnerRunReceipt.model_validate_json((tmp_path / "owner-receipt.json").read_bytes())
    _verify(tmp_path, receipt)
    status_only = [h for h in receipt.heads if h.module_id == "CP-1D"]
    assert [h.status for h in status_only] == ["blocked"]


# --- A4 tamper at verifier level ----------------------------------------------------------------


def test_tampering_refuses_with_identity_mismatch(closed: Closed, tmp_path: Path) -> None:
    """The audit and the pre-probe checks pass on a consistently forged read body; the view
    replay refuses; an edited step output, SettledHead or retained step makes `probe` raise."""
    root = tmp_path / "audit"
    root.mkdir()
    shutil.copytree(closed.root / "store", root / "store")
    _verify(root, closed.receipt)

    def refuses(receipt: Any = closed.receipt) -> None:
        with pytest.raises(WorkflowError) as caught:
            _verify(root, receipt)
        assert caught.value.code == "identity_mismatch"

    reads = root / "store/owner-run-audit/input-reads"
    old = next(r for r in closed.receipt.input_reads if r.binding.module_id == "CP-1D")
    assert "cp1_facts_note" in old.body
    body = old.body.replace("cp1_facts_note", "cp1_facts_notX", 1)
    edited = old.model_copy(
        update={"body": body, "inputs_sha256": hashlib.sha256(body.encode()).hexdigest()}
    )
    forged = closed.receipt.model_copy(
        update={"input_reads": tuple(edited if r == old else r for r in closed.receipt.input_reads)}
    )
    (reads / old.content_hash()).unlink()
    (reads / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    sealed = root / "store/owner-run-audit/receipt.sha256"
    sealed.write_text(forged.content_hash())
    store = Execution(root / "store")
    _verify_audit(store, forged)  # the audit and the seal agree with the forged copy ...
    with pytest.raises(WorkflowError) as replay:  # ... so the view replay is what refuses
        _verify_calls_reads(store, forged, OWNER_SPECS)
    assert replay.value.code == "identity_mismatch"
    refuses(forged)
    (reads / edited.content_hash()).unlink()
    (reads / old.content_hash()).write_bytes(old.model_dump_json().encode())
    sealed.write_text(closed.receipt.content_hash())
    _verify(root, closed.receipt)

    # an edited CP-1D SettledHead
    heads = tuple(
        h.model_copy(update={"status": "accepted"}) if h.module_id == "CP-1D" else h
        for h in closed.receipt.heads
    )
    refuses(closed.receipt.model_copy(update={"heads": heads}))
    wrong = tuple(
        h.model_copy(update={"result_sha256": "0" * 64}) if h.module_id == "CP-1D" else h
        for h in closed.receipt.heads
    )
    refuses(closed.receipt.model_copy(update={"heads": wrong}))

    # probe itself: the retained step swapped for another payload under the same attempt
    live = Execution(root / "store")
    attempt = _attempts(live, "CP-1D")[0]
    other = json.loads(live.payload(attempt.steps[0].payload_sha256))
    other["overall"]["rationale"] += " Reviewed."
    forged_step = attempt.steps[0].model_copy(
        update={"payload_sha256": live._store(json.dumps(other))}
    )
    with pytest.raises(WorkflowError) as probed:
        cp1d.probe(live, live.read(), attempt.model_copy(update={"steps": (forged_step,)}))
    assert probed.value.code == "identity_mismatch"


# --- A5: the shipped owner workflows are unchanged -------------------------------------------------
# `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` run unchanged (deferred commands).
