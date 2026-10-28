"""CP-2A store runs (Stage 5 only): genuine CP-0 and CP-1 promotions, then CP-2A, through the
public `OwnerWorkflow` API, compared with `cases/cp2a-owner/expected.json`. Each case is 11-26
minutes (module-scoped fixtures, one job under the heavy-job lock). Written in Stage 2, never run
there. Covers the lease Acceptance section (:167-177) item by item:

- A1 positive: plan order, statuses, every fact's status, unit, period, amount and shown text,
  the claims, own limitations, one ok `read_inputs` and no ok pack call;
- A2 gap (base Q3 25); A2b refused (one `RefusedBegin` for CP-1, no CP-2A anywhere);
- A2d blocked; A2e the CP-1 readiness row is `ready_with_limitations`;
- A3 clones: `read_pages` refused, submit before read `not_permitted`, a changed snapshot
  `stale_binding`, an unreplaced figure invalid (the same three also run in seconds in
  `tests/test_connect_cp2a.py` over hand-seeded heads);
- A4 tamper: an edited read body, step output or `SettledHead` is `identity_mismatch`, and the
  verifier reaches `_PROBES["CP-2A"]` and writes nothing.

The consumption proof (D3) is CP-2G's. A5 (`test_owner_workflow.py`, `test_owner_s1a.py`) is run
as its own files.
"""

import hashlib
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from cp2a_runs import bound_literal, cp2a_closed, oracle, promoted
from s1a_runs import clone_workflow

from deploy_vii.downstream_readiness import ConsumerRequest, ConsumerRow, DownstreamReport
from deploy_vii.execution import Execution
from deploy_vii.report_view import fact_spelling
from deploy_workflow import owner_workflow as ow
from deploy_workflow.financial_workflow import _put
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.workflow import WorkflowError

EXPECTED: dict[str, Any] = oracle()["expected"]
SUBMISSIONS: dict[str, Any] = oracle()["submissions"]
Closed = tuple[Path, Path, None]
FIG = re.compile(r"\{\{FIG:([a-z_]+)\|([^}]*)\}\}")


@pytest.fixture(scope="module")
def positive(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return cp2a_closed("positive", tmp_path_factory.mktemp("cp2a-positive"))


@pytest.fixture(scope="module")
def gap(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return cp2a_closed("gap", tmp_path_factory.mktemp("cp2a-gap"))


@pytest.fixture(scope="module")
def refused(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return cp2a_closed("refused", tmp_path_factory.mktemp("cp2a-refused"))


@pytest.fixture(scope="module")
def blocked(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return cp2a_closed("blocked", tmp_path_factory.mktemp("cp2a-blocked"))


@pytest.fixture(scope="module")
def ready(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    """CP-0 and CP-1 settled and CP-2A begun, untouched (the slow part, built once)."""
    return promoted("positive", tmp_path_factory.mktemp("cp2a-ready"))[0]


def _receipt(closed: Closed) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json(closed[1].read_bytes())


def _verify(closed: Closed) -> Execution:
    store = Execution(closed[0])
    ow.verify_owner_run_receipt(store, _receipt(closed))
    return store


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _assert_head_equals_oracle(store: Execution, case: str) -> None:
    """Status, unit, period, amount, shown text, value class and claims of the settled head."""
    want = EXPECTED["cases"][case]
    module = store.head_module(_head(store, "CP-2A"))
    assert module.status == "restricted"
    mine = [f for f in module.facts if f.table_id != "cp1_references"]
    assert [f.fact_id for f in mine] == [e["fact_id"] for e in want["facts"]]
    for fact, expected in zip(mine, want["facts"], strict=True):
        assert fact.status == expected["status"], fact.fact_id
        assert fact.unit == expected.get("unit"), fact.fact_id
        assert fact.period == expected.get("period"), fact.fact_id
        assert fact.value_class == expected.get("value_class"), fact.fact_id
        if expected.get("amount_exact") is not None:
            assert fact.amount == Decimal(expected["amount_exact"]), fact.fact_id
        if fact.status == "known":
            assert fact_spelling(fact, None)[2] == expected["shown"], fact.fact_id
    assert [t.table_id for t in module.tables if t.table_id.startswith("T2B.")] == [
        t["table_id"] for t in want["tables"]
    ]
    # Claims carry the CP-1 fact ids bound at run time (the manifest's selection rule).
    cp1 = store.head_module(_head(store, "CP-1")).facts
    ids = {
        name: next(
            f.fact_id for f in cp1 if f.table_id == "T4.10" and f.label == figure["cp1_label"]
        )
        for name, figure in SUBMISSIONS["figures"].items()
    }
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in want["claims"]]
    for claim, expected in zip(module.claims, want["claims"], strict=True):
        assert claim.text == FIG.sub(lambda m: "{" + ids[m[1]] + "|" + m[2] + "}", expected["text"])
        assert claim.limitation == expected["limitation"], claim.claim_id
    assert list(module.limitations[: len(want["own_limitations"])]) == want["own_limitations"]


# --- A1 positive ------------------------------------------------------------------------------


def test_a1_positive_head_equals_the_oracle(positive: Closed) -> None:
    store = _verify(positive)
    assert [h.module_id for h in store.read().heads] == EXPECTED["execution"]["plan_order"]
    assert _receipt(positive).plan == tuple(EXPECTED["execution"]["plan_order"])
    assert {h.module_id: h.status for h in store.read().heads} == {
        "CP-0": "restricted",
        "CP-1": "restricted",
        "CP-2A": "restricted",
    }
    _assert_head_equals_oracle(store, "positive")


def test_a1_one_ok_read_and_no_ok_pack_call_in_the_cp2a_step(positive: Closed) -> None:
    receipt = _receipt(positive)
    reads = [r for r in receipt.input_reads if r.binding.module_id == "CP-2A"]
    calls = [c for c in receipt.calls if c.binding.module_id == "CP-2A"]
    assert len(reads) == 1
    assert not [c for c in calls if c.status == "ok"]
    assert all(c.error_code == "not_permitted" for c in calls)
    assert reads[0].inputs_sha256 == hashlib.sha256(reads[0].body.encode()).hexdigest()


def test_a1_the_settled_head_is_bound_to_its_tail_input(positive: Closed) -> None:
    store = _verify(positive)
    module = store.head_module(_head(store, "CP-2A"))
    assert module.inputs[-1].input_id == "downside-pathway-submission"
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-2A")
    assert attempt.result_sha256 == _head(store, "CP-2A").result_sha256


# --- A2 gap, A2b refused, A2d blocked, A2e CP-1 readiness ------------------------------------


def test_a2_gap_base_q3_composes_gaps_never_zero(gap: Closed) -> None:
    store = _verify(gap)
    _assert_head_equals_oracle(store, "gap")
    module = store.head_module(_head(store, "CP-2A"))
    ratios = [f for f in module.facts if f.table_id == "T2B.4" and f.field.endswith("leverage")]
    assert ratios and all(f.status != "known" and f.amount is None for f in ratios)


def test_a2b_refused_begin_for_cp1_and_no_cp2a_anywhere(refused: Closed) -> None:
    store = _verify(refused)
    receipt = _receipt(refused)
    want = EXPECTED["cases"]["refused"]["refused_begins"]
    assert [(r.module_id, r.reason) for r in receipt.refusals] == [
        (w["module_id"], w["reason"]) for w in want
    ]
    assert len(receipt.refusals) == 1
    snapshot = store.read()
    assert [h.module_id for h in snapshot.heads] == EXPECTED["cases"]["refused"]["heads"]
    assert {a.module_id for a in snapshot.attempts} == set(EXPECTED["cases"]["refused"]["attempts"])
    commands = [(c.row_id, c.text) for c in _head(store, "CP-0").commands]
    assert commands == [tuple(c) for c in EXPECTED["cases"]["refused"]["cp0"]["T8_commands"]]
    assert not [a for a in snapshot.attempts if a.module_id == "CP-2A"]
    assert not [h for h in snapshot.heads if h.module_id == "CP-2A"]
    assert _head(store, "CP-0").status == EXPECTED["cases"]["refused"]["cp0"]["settled_status"]


def test_a2d_blocked_run_leaves_a_blocked_head_and_a_verifying_receipt(blocked: Closed) -> None:
    store = _verify(blocked)
    expected = EXPECTED["cases"]["blocked"]
    head = _head(store, "CP-2A")
    module = store.head_module(head)
    assert head.status == expected["head"]["status"] == "blocked"
    assert list(module.limitations) == expected["attempt_1"]["limitations"]
    assert module.tables == () and module.facts == ()
    attempts = [a for a in store.read().attempts if a.module_id == "CP-2A"]
    assert [a.number for a in attempts] == [0, 1] and attempts[1].repair_of == attempts[0].ticket_id
    assert list(attempts[0].issues) == expected["attempt_0"]["limitations"]
    assert [h.status for h in _receipt(blocked).heads if h.module_id == "CP-2A"] == ["blocked"]


def cp2a_consumer_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """The `consumers` rows of a CP-1 readiness `DownstreamReport` whose canonical module is
    CP-2A. The same entry also appears in `inputs.consumers` (the request) and in
    `review.consumers` (the assessment), neither of which carries a `status`."""
    rows: list[dict[str, Any]] = report["consumers"]
    return [r for r in rows if r["canonical_module"] == "CP-2A"]


def test_cp2a_consumer_rows_ignore_the_request_and_the_assessment() -> None:
    """Fast: the selector over the report's three places that name CP-2A (shape from the oracle
    review literal and the real model field sets) returns only the one `consumers` row."""
    review = SUBMISSIONS["cp1_downstream_review"]["consumers"]
    assert {"entry"} <= set(ConsumerRequest.model_fields) & set(ConsumerRow.model_fields)
    assert {"inputs", "review", "consumers"} <= set(DownstreamReport.model_fields)
    shape = {
        "inputs": {"consumers": [{"entry": "CP-2A", "canonical_module": "CP-2A"}]},
        "review": {"consumers": review},
        "consumers": [
            {"entry": "CP-2A", "canonical_module": "CP-2A", "status": "ready_with_limitations"},
            {"entry": "CP-9", "canonical_module": "CP-9", "status": "ready"},
        ],
    }
    rows = cp2a_consumer_rows(shape)
    assert [r["status"] for r in rows] == ["ready_with_limitations"]


def test_a2e_cp1_readiness_row_for_cp2a_is_ready_with_limitations(positive: Closed) -> None:
    store = _verify(positive)
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    step = next(s for s in attempt.steps if s.step_id == "readiness")
    output = store.step_output(step.output_sha256 or "")
    DownstreamReport.model_validate_json(output)  # the real report shape, not a guess
    rows = cp2a_consumer_rows(json.loads(output))
    row = EXPECTED["cp1_readiness"]["consumer_row"]
    assert len(rows) == 1
    assert (rows[0]["canonical_module"], rows[0]["status"]) == (
        row["canonical_module"],
        "ready_with_limitations",
    )
    assert row["status"] == "ready_with_limitations"


# --- A3 clones (forks of the ready state; each takes the step's first call) ---------------------


def test_a3_pack_tools_refused_and_submit_before_read_not_permitted(
    ready: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(ready, tmp_path)
    for tool, arguments in (
        ("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}),
        ("search_pack", {"query": "debt", "source_id": "financial"}),
    ):
        call = workflow.invoke(tool, arguments)
        assert (call["status"], call["error_code"], call["body"]) == (
            "refused",
            "not_permitted",
            None,
        )
    payload = json.dumps(SUBMISSIONS["positive"]["downside_pathway"])
    with pytest.raises(WorkflowError) as unread:
        workflow.submit_review(payload)
    assert unread.value.code == "not_permitted"
    assert not [s for s in workflow._submissions if s.binding.binding.module_id == "CP-2A"]


def test_a3_snapshot_change_between_read_and_submit_is_stale_binding(
    ready: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(ready, tmp_path)
    body = json.loads(workflow.read_inputs()["body"])
    Execution(tmp_path / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    payload = SUBMISSIONS["positive"]["downside_pathway"]
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(bound_literal(workflow, payload, body))
    assert caught.value.code == "stale_binding"


def test_a3_unreplaced_figure_is_invalid(ready: OwnerWorkflow, tmp_path: Path) -> None:
    workflow = clone_workflow(ready, tmp_path)
    workflow.read_inputs()
    outcome = workflow.submit_review(json.dumps(SUBMISSIONS["positive"]["downside_pathway"]))
    assert outcome["status"] == "invalid"
    assert any("Malformed run text" in issue for issue in outcome["issues"]), outcome["issues"]


# --- A4 tamper at the verifier ------------------------------------------------------------------


def _copy(closed: Closed, tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "audit"
    root.mkdir()
    shutil.copytree(closed[0], root / "store")
    return root, closed[1]


def _verdict(store: Execution, receipt: OwnerRunReceipt) -> str:
    try:
        ow.verify_owner_run_receipt(store, receipt)
    except WorkflowError as error:
        return error.code
    return "accepted"


def test_a4_untouched_copy_verifies_and_verification_writes_nothing(
    positive: Closed, tmp_path: Path
) -> None:
    root, _ = _copy(positive, tmp_path)
    before = _tree(root / "store")
    assert _verdict(Execution(root / "store"), _receipt(positive)) == "accepted"
    assert _tree(root / "store") == before


def test_a4_edited_read_body_is_identity_mismatch(positive: Closed, tmp_path: Path) -> None:
    root, _ = _copy(positive, tmp_path)
    receipt = _receipt(positive)
    store = Execution(root / "store")
    old = next(r for r in receipt.input_reads if r.binding.module_id == "CP-2A")
    body = old.body.replace("cp1_facts_note", "cp1_facts_notX", 1)
    assert body != old.body
    edited = old.model_copy(
        update={"body": body, "inputs_sha256": hashlib.sha256(body.encode()).hexdigest()}
    )
    forged = receipt.model_copy(
        update={"input_reads": tuple(edited if r == old else r for r in receipt.input_reads)}
    )
    reads = root / "store" / ow.AUDIT / "input-reads"
    (reads / old.content_hash()).unlink()
    ow._retain(store, "input-reads", edited)
    seal = root / "store" / ow.AUDIT / "receipt.sha256"
    seal.unlink()
    _put(seal, forged.content_hash().encode())
    ow._verify_audit(store, forged)  # the audit and the seal agree with the forged copy ...
    assert _verdict(store, forged) == "identity_mismatch"  # ... so the view replay refuses it


def test_a4_edited_step_output_is_identity_mismatch(positive: Closed, tmp_path: Path) -> None:
    root, _ = _copy(positive, tmp_path)
    store = Execution(root / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-2A")
    blob = root / "store" / "blobs" / (attempt.steps[0].output_sha256 or "")
    original = blob.read_bytes()
    blob.write_bytes(original + b" ")
    assert _verdict(store, _receipt(positive)) == "identity_mismatch"
    blob.write_bytes(original)
    assert _verdict(store, _receipt(positive)) == "accepted"


def test_a4_edited_settled_head_is_identity_mismatch(positive: Closed, tmp_path: Path) -> None:
    root, _ = _copy(positive, tmp_path)
    store = Execution(root / "store")
    receipt = _receipt(positive)
    for update in ({"status": "accepted"}, {"result_sha256": "0" * 64}):
        heads = tuple(
            h.model_copy(update=update) if h.module_id == "CP-2A" else h for h in receipt.heads
        )
        assert _verdict(store, receipt.model_copy(update={"heads": heads})) == "identity_mismatch"


def test_a4_the_verifier_reaches_the_cp2a_probe_after_the_audit_checks(
    positive: Closed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = _copy(positive, tmp_path)
    seen: list[str] = []

    def probe(store: Execution, snapshot: Any, attempt: Any) -> None:
        seen.append(attempt.module_id)
        raise WorkflowError("identity_mismatch")

    monkeypatch.setitem(ow._PROBES, "CP-2A", probe)
    assert _verdict(Execution(root / "store"), _receipt(positive)) == "identity_mismatch"
    assert seen == ["CP-2A"]
