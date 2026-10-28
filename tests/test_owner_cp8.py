"""CP-8 store runs: lease acceptance 1-3, 5 (run level) and 6, and the D3 reader pin (D3 is OPEN).

Each run takes well under a second. Expected values are read from `cases/cp8-owner/expected.json`
and `submissions.json` only. The product's `settle` is the truth for a head's limitations: for a
synthetic run it adds "Synthetic case; not real issuer qualification" to the own list (Stage 2
round 3 ruling), which the oracle's own list does not hold.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import cp8_runs as runs
import pytest

from deploy_vii.execution import Execution, inherited_limitations
from deploy_vii.live.tools import UNBACKED_ABSENCE
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owners import cp8
from deploy_workflow.workflow import WorkflowError

ORACLE = runs.oracle()
EXPECTED = ORACLE["expected"]
SUBMISSIONS = ORACLE["submissions"]
SYNTHETIC = "Synthetic case; not real issuer qualification"
NOT_AUTHORIZED = "CP-0 has not authorized this consumer's source readiness"
ENTRIES = {e["id"]: e for e in SUBMISSIONS["refusal_mutations"]["entries"]}
PINNED = {r["id"]: r for r in EXPECTED["refusals"]}


def own_limitations(case: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*EXPECTED["cases"][case]["own_limitations"], SYNTHETIC)))


def inherited(case: str) -> tuple[str, ...]:
    return tuple(t for t in EXPECTED["cases"][case]["inherited_limitations"] if t != SYNTHETIC)


def head_of(root: Path) -> tuple[Execution, Any]:
    store = Execution(root / "store")
    return store, next(h for h in store.read().heads if h.module_id == "CP-8")


def attempts(root: Path) -> list[Any]:
    return [a for a in Execution(root / "store").read().attempts if a.module_id == "CP-8"]


def cover(case: str) -> list[list[str]]:
    pages: list[list[str]] = EXPECTED["cases"][case]["tool_use_required"]["read_pages_cover"]
    return pages


# --- acceptance 1 and 2: the closed runs -------------------------------------------------------------


@pytest.mark.parametrize("case", ["positive", "no_outcome"])
def test_closed_run_settles_restricted_with_the_expected_tables(case: str, tmp_path: Path) -> None:
    runs.cp8_closed(case, tmp_path)
    store, head = head_of(tmp_path)
    module = store.head_module(head)
    expected = EXPECTED["cases"][case]
    assert head.status == module.status == expected["status"]
    assert [i.input_id for i in module.inputs] == expected["module_inputs"]
    assert [t.table_id for t in module.tables] == [t["table_id"] for t in expected["tables"]]
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in expected["claims"]]
    assert module.limitations == own_limitations(case)
    assert module.inherited_limitations == inherited(case)
    snapshot = store.read()
    attempt = attempts(tmp_path)[0]
    assert module.inherited_limitations == inherited_limitations(
        snapshot, attempt, module.limitations, store.head_module
    )


@pytest.mark.parametrize("case", ["positive", "no_outcome"])
def test_the_reader_returns_the_settled_own_limitations(case: str, tmp_path: Path) -> None:
    """Pinned on a head built by `settle` (the real run), not by hand."""
    runs.cp8_closed(case, tmp_path)
    store, head = head_of(tmp_path)
    got = cp8.cp8_reader(store, head)
    assert got.limitations == store.head_module(head).limitations == own_limitations(case)
    assert got.limitations[-1] == SYNTHETIC
    assert got.status == head.status


def test_receipt_verifies_and_probe_rebuilds(tmp_path: Path) -> None:
    workflow, _ = runs.cp8_closed("positive", tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)
    store, head = head_of(tmp_path)
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    cp8.probe(store, snapshot, attempt)


def test_d3_the_reader_exposes_the_pinned_head_and_claims_no_consumption(tmp_path: Path) -> None:
    """D3 is OPEN (lease :93): no consumer core reads CP-8. This pins what the reader exposes
    over a settled head and the inputs it hash-binds; it is not a consumption proof."""
    runs.cp8_closed("positive", tmp_path)
    store, head = head_of(tmp_path)
    pinned = EXPECTED["consumption"]["reader_pinned"]["positive_values"]
    got = cp8.cp8_reader(store, head)
    assert got.head_sha256 == head.result_sha256
    assert (got.overall_label, got.overall_process_sound) == (
        pinned["overall"],
        pinned["process_sound"],
    )
    assert str(got.window_days) == str(pinned["window_days"])
    assert dict(got.directions) == pinned["directions"]
    assert EXPECTED["consumption"]["status"] == "OPEN"
    cp0 = next(h for h in store.read().heads if h.module_id == "CP-0")
    module = store.head_module(head)
    assert next(i for i in module.inputs if i.input_id == "CP-0").sha256 == cp0.result_sha256


# --- acceptance 3: no record ------------------------------------------------------------------------


def test_no_record_cp0_says_do_not_run_and_begin_is_refused(tmp_path: Path) -> None:
    workflow, _ = runs.start("no_record", tmp_path)
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    cp0 = next(h for h in snapshot.heads if h.module_id == "CP-0")
    assert [c.text for c in cp0.commands if c.row_id == "CP-8"] == ["DO NOT RUN"]
    assert attempts(tmp_path) == []
    assert not [h for h in snapshot.heads if h.module_id == "CP-8"]
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [(r.module_id, r.reason) for r in receipt.refusals] == [("CP-8", NOT_AUTHORIZED)]
    owner.verify_owner_run_receipt(store, receipt)


# --- acceptance 5 at run level: the journaled tuple ---------------------------------------------------


def run_literal(tmp_path: Path, case: str, payload: dict[str, Any]) -> dict[str, Any]:
    workflow, _ = runs.start(case, tmp_path)
    return runs.submit(workflow, json.dumps(payload), read=cover(case), searched=True)


@pytest.mark.parametrize("rid", sorted(ENTRIES))
def test_a_refusal_is_journaled_as_validator_issues_then_rules_issues(
    rid: str, tmp_path: Path
) -> None:
    entry = ENTRIES[rid]
    outcome = run_literal(tmp_path, entry["base"], entry["literal"])
    assert outcome["status"] == "invalid"
    assert tuple(outcome["issues"]) == tuple(PINNED[rid]["issues"])
    assert PINNED[rid]["issues"] == entry["validator_issues"] + entry["rules_issues"]


def test_the_shape_refusal_is_journaled(tmp_path: Path) -> None:
    literal = SUBMISSIONS["shape_refusal"]
    outcome = run_literal(tmp_path, literal["base"], literal["literal"])
    assert outcome["status"] == "invalid"
    assert outcome["issues"] == literal["issues"] == PINNED["r00"]["issues"]


def test_r42_is_journaled_twice_not_deduplicated(tmp_path: Path) -> None:
    outcome = run_literal(tmp_path, "positive", ENTRIES["r42"]["literal"])
    issues = outcome["issues"]
    assert len(issues) == 2 and issues[0] == issues[1]
    attempt = attempts(tmp_path)[0]
    assert tuple(attempt.steps[0].issues) == tuple(issues)  # the journaled step keeps both


@pytest.mark.parametrize("item", SUBMISSIONS["tool_use_refusals"], ids=lambda i: i["id"])
def test_tool_use_refusals_t01_to_t03(item: dict[str, Any], tmp_path: Path) -> None:
    workflow, _ = runs.start("positive", tmp_path)
    payload = json.dumps(SUBMISSIONS[item["literal"]])
    outcome = runs.submit(workflow, payload, read=item["read"], searched=item["searched"])
    assert outcome["status"] == "invalid"
    assert tuple(outcome["issues"]) == tuple(item["issues"])
    if not item["searched"]:
        assert outcome["issues"] == [UNBACKED_ABSENCE]


def test_the_blocked_case_attempt_0_r23_then_attempt_1_r03(tmp_path: Path) -> None:
    blocked = SUBMISSIONS["blocked"]
    expected = EXPECTED["blocked"]
    workflow, _ = runs.start("positive", tmp_path)
    first = runs.submit(
        workflow, json.dumps(blocked["attempt_0"]["literal"]), read=cover("positive")
    )
    assert first["status"] == "invalid"
    assert first["issues"] == expected["attempt_0_issues"]
    second = runs.submit(
        workflow, json.dumps(blocked["attempt_1"]["literal"]), read=cover("positive")
    )
    assert second["issues"] == expected["attempt_1_issues"]
    store, head = head_of(tmp_path)
    module = store.head_module(head)
    first_attempt, second_attempt = attempts(tmp_path)
    assert (first_attempt.number, second_attempt.number) == (0, 1)
    assert second_attempt.repair_of == first_attempt.ticket_id
    assert head.status == module.status == "blocked"
    assert module.tables == () and module.claims == ()
    assert module.limitations == tuple(expected["attempt_1_issues"])


# --- G1-level refusals --------------------------------------------------------------------------------


def test_extract_statements_and_read_inputs_are_not_permitted(tmp_path: Path) -> None:
    workflow, _ = runs.start("positive", tmp_path)
    call = workflow.invoke("extract_statements", {"source_id": "prior_case"})
    assert (call["status"], call["error_code"]) == ("refused", "not_permitted")
    with pytest.raises(WorkflowError) as caught:
        workflow.read_inputs()
    assert caught.value.code == "not_permitted"


def test_identity_is_outside_the_host_scope(tmp_path: Path) -> None:
    workflow, _ = runs.start("positive", tmp_path)
    call = workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
    assert call["status"] != "ok"


def test_a_snapshot_change_between_the_last_read_and_the_submit_is_stale(tmp_path: Path) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    payload = runs.literal("positive", "submission", pack)
    runs.read_pages(workflow, cover("positive"))
    store = Execution(tmp_path / "store")
    store.interrupt(attempts(tmp_path)[0].ticket_id, "external change between read and submit")
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(payload)
    assert caught.value.code == "stale_binding"


# --- acceptance 6: tamper ----------------------------------------------------------------------------


def forge(root: Path, receipt: Any) -> tuple[Execution, Any, Any, Any]:
    """The lease recipe on a copy of the closed positive store: the CP-8 result Module's fact
    T7.4.total_leverage.direction Higher -> Lower, re-hashed through the snapshot, the head, the
    receipt and the audit files, so only the probe's rebuild can refuse it."""
    shutil.copytree(root / "store", root / "audit" / "store")
    store = Execution(root / "audit" / "store")
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-8")
    module = store.head_module(head)
    target = "T7.4.total_leverage.direction"
    assert next(f for f in module.facts if f.fact_id == target).text == "Higher"
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": "Lower"}) if f.fact_id == target else f
                for f in module.facts
            )
        }
    )
    r2 = store._store(forged.model_dump_json())
    assert r2 == forged.content_hash() != head.result_sha256
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    new_attempt = attempt.model_copy(update={"result_sha256": r2})
    new_snapshot = snapshot.model_copy(
        update={
            "heads": tuple(
                h.model_copy(update={"result_sha256": r2}) if h.module_id == "CP-8" else h
                for h in snapshot.heads
            ),
            "attempts": tuple(
                new_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            ),
        }
    )
    store._write(new_snapshot)
    digest = new_snapshot.content_hash()
    old = next(
        s
        for s in reversed(receipt.submissions)
        if s.binding.binding.module_id == "CP-8" and s.disposition == "valid"
    )
    edited = old.model_copy(update={"snapshot_after_sha256": digest})
    forged_receipt = receipt.model_copy(
        update={
            "snapshot_sha256": digest,
            "heads": tuple(
                h.model_copy(update={"result_sha256": r2}) if h.module_id == "CP-8" else h
                for h in receipt.heads
            ),
            "submissions": tuple(edited if s == old else s for s in receipt.submissions),
        }
    )
    audit = store.directory / owner.AUDIT
    (audit / "submissions" / old.content_hash()).unlink()
    (audit / "submissions" / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    (audit / "receipt.sha256").write_text(forged_receipt.content_hash())
    return store, new_snapshot, new_attempt, forged_receipt


def test_tamper_is_caught_by_the_probe_after_every_earlier_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow, _ = runs.cp8_closed("positive", tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner.verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)
    (tmp_path / "audit").mkdir()
    store, snapshot, attempt, forged = forge(tmp_path, receipt)
    owner._verify_audit(store, forged)  # the audit and the seal agree with the forged copy ...
    reached: list[str] = []
    real = owner._PROBES["CP-8"]

    def spy(s: Execution, snap: Any, att: Any) -> None:
        reached.append(att.module_id)
        real(s, snap, att)

    monkeypatch.setitem(owner._PROBES, "CP-8", spy)
    with pytest.raises(WorkflowError) as caught:  # ... so the probe is what refuses it
        owner.verify_owner_run_receipt(store, forged)
    assert caught.value.code == "identity_mismatch"
    assert reached == ["CP-8"]
    with pytest.raises(WorkflowError) as direct:
        cp8.probe(store, snapshot, attempt)
    assert direct.value.code == "identity_mismatch"
