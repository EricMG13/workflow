"""CP-4C store runs (Stage 5 only): genuine CP-0 and CP-1 promotions, the frozen CP-2A, CP-4 and
CP-2G literals, then CP-4C, through the public `OwnerWorkflow` API, compared with
`cases/cp4c-owner/expected.json`. Each closed case is 11-26 minutes (module-scoped fixtures, one
job under the heavy-job lock). Written in Stage 2, never run there. Covers the lease Acceptance
section item by item:
- A1 positive: plan order and inputs, statuses, every T4E fact record, the reference tables,
  claims, own limitations, the tool use (one ok `read_inputs`, the oracle's reads and searches,
  no other ok call), the tail input, and the first-run T4.18 confirmation (open question 8);
- A2 gap; A2b refused; A2c blocked and cp2g_blocked; A2d the composer-only fixtures;
- A3 every refusal at run level (clones), the stale_binding clone per upstream, the tool-use
  refusals and model text at run level;
- A4 tamper (`expected.json#tamper`, the CP-DR `_forge` shape); A6 consumption on genuine heads;
  A7 the bindings and FP05 spellings on the settled head (the G2 page is Stage 3).
The fast forms over hand-seeded heads are `tests/test_connect_cp4c.py`. A5 (`test_owner_workflow.py`,
`test_owner_s1a.py`, the CP-2A, CP-4 and CP-2G owner tests) is run as its own files.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import cp4c_runs as runs
import pytest
import test_method_cp4c as stage1
import view_tree
from defect_classes import model_text_failures
from s1a_runs import clone_workflow
from test_connect_cp4c import CP4C_VERBATIM

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import ModuleView, View
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, head_of
from deploy_vii.live.tools import UNREAD_PAGE
from deploy_vii.report_view import fact_spelling
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.owners import cp2g, cp4c
from deploy_workflow.workflow import WorkflowError

EXPECTED: dict[str, Any] = runs.oracle()["expected"]
SUBMISSIONS: dict[str, Any] = runs.oracle()["submissions"]
MANIFEST: dict[str, Any] = runs.oracle()["manifest"]
MODULE = "CP-4C"
STEP = runs.STEP
SYNTHETIC = "Synthetic case; not real issuer qualification"
Closed = tuple[Path, Path, None]
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\|([^}]*)\}\}")
FACT_ID = re.compile(r"\{\{FACT_ID:([a-z_0-9]+)\}\}")
REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
EXPECTED_REFUSALS = {r["id"]: r for r in EXPECTED["refusals"]}
STALE = ("v24", "v25", "v26", "v27")
RUN_LEVEL = [rid for rid in REFUSALS if rid not in STALE]
REFERENCES = ("cp1_references", "cp2g_references", "cp2a_references", "cp4_references")


@pytest.fixture(scope="module")
def positive(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp4c_closed("positive", tmp_path_factory.mktemp("cp4c-positive"))


@pytest.fixture(scope="module")
def gap(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp4c_closed("gap", tmp_path_factory.mktemp("cp4c-gap"))


@pytest.fixture(scope="module")
def blocked(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp4c_closed("blocked", tmp_path_factory.mktemp("cp4c-blocked"))


@pytest.fixture(scope="module")
def refused(tmp_path_factory: pytest.TempPathFactory) -> tuple[Closed, dict[str, Any]]:
    """CP-0 only; the CP-0 submit's outcome (it carries the begin refusal) is kept."""
    root = tmp_path_factory.mktemp("cp4c-refused")
    workflow, pack = runs.start("refused", root)
    outcome = runs.drive_cp0(workflow, pack, "refused")
    workflow.write_receipt(root / "owner-receipt.json")
    return (root / "store", root / "owner-receipt.json", None), outcome


@pytest.fixture(scope="module")
def cp2g_blocked(tmp_path_factory: pytest.TempPathFactory) -> tuple[Closed, dict[str, Any]]:
    """CP-2G r01 then v13 (its own oracle); the attempt-1 outcome (the CP-4C begin refusal)."""
    root = tmp_path_factory.mktemp("cp4c-cp2g-blocked")
    workflow, _ = runs.promoted("cp2g_blocked", root)
    runs.drive_cp2a(workflow)
    runs.drive_cp4(workflow, "cp2g_blocked")
    cp2g_runs = runs._driver("cp2g_runs")
    refusals = {r["id"]: r for r in cp2g_runs.oracle()["submissions"]["refusals"]}
    outcome: dict[str, Any] = {}
    for rid in ("r01", "v13"):
        outcome = cp2g_runs.drive_cp2g(workflow, refusals[rid]["payload"])
    workflow.write_receipt(root / "owner-receipt.json")
    return (root / "store", root / "owner-receipt.json", None), outcome


@pytest.fixture(scope="module")
def waiting(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    """Every upstream settled, CP-4C begun and untouched (positive; the slow part, built once)."""
    return runs.ready("positive", tmp_path_factory.mktemp("cp4c-ready"))


def _receipt(closed: Closed) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json(closed[1].read_bytes())


def _verify(closed: Closed) -> Execution:
    store = Execution(closed[0])
    ow.verify_owner_run_receipt(store, _receipt(closed))
    return store


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _fig_ids(store: Execution) -> dict[str, str]:
    """FIG name -> the fact id bound at run time (`run_time_bindings.figure_placeholders`)."""
    cp1 = store.head_module(_head(store, "CP-1")).facts
    out: dict[str, str] = {}
    for name, figure in SUBMISSIONS["figures"].items():
        if figure["source"] == "cp2g":
            out[name] = figure["fact_id"]
        else:
            label = f"{runs.LTM_LABEL} · {figure['metric']}"
            out[name] = next(f.fact_id for f in cp1 if f.table_id == "T4.10" and f.label == label)
    return out


def _bind(text: str, ids: dict[str, str]) -> str:
    return FIG.sub(lambda m: "{" + ids[m[1]] + "|" + m[2] + "}", text)


def _assert_head_equals_oracle(store: Execution, case: str) -> None:
    """Every T4E fact record and spelling (a settled Fact stores no lineage: that is A6's), the
    tables, the reference tables, the claims (text with the run-time ids) and limitations."""
    want = EXPECTED["cases"][case]
    module = store.head_module(_head(store, MODULE))
    assert module.status == want["module_status"] == "restricted"
    own = [f for f in module.facts if f.table_id.startswith("T4E.")]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    for fact, e in zip(own, want["facts"], strict=True):
        cell = cp4c.Cell(fact, tuple(e.get("derives_from", ())), (), e["shown"])
        assert stage1._record(cell) == {k: v for k, v in e.items() if k != "citations"}, e
        _uc, _state, text = fact_spelling(fact, "G1")
        if e["shown"] is None:  # unsettled: the manifest's cell_notation spelling
            shown = {"missing": "∅ G#", "not_applicable": "∅ G# n.m."}[e["status"]]
        else:
            shown = e["shown"]
        assert text.replace("G1", "G#") == shown, fact.fact_id
    for table, e in zip(module.tables, want["tables"], strict=False):
        assert (table.table_id, table.title) == (e["table_id"], e["title"])
        assert [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] == [
            (r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]
        ]
    by_id = {f.fact_id: f for f in module.facts}
    for name in REFERENCES:
        table = next(t for t in module.tables if t.table_id == name)
        rows = want[name]["rows"]
        assert [(r.row_id, r.label) for r in table.rows] == [
            (r["row_id"], r["label"]) for r in rows
        ]
        for row, e in zip(table.rows, rows, strict=True):
            fact = by_id[row.fact_ids[0]]
            assert (fact.status, stage1._norm(fact.amount)) == (e["status"], e["amount_exact"])
    ids = _fig_ids(store)
    assert [(c.claim_id, c.text, c.citations, c.limitation) for c in module.claims] == [
        (c["claim_id"], _bind(c["text"], ids), (), c["limitation"]) for c in want["claims"]
    ]
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]


# --- A1 positive ------------------------------------------------------------------------------


def test_a1_positive_heads_inputs_and_the_cp4c_head(positive: Closed) -> None:
    store = _verify(positive)
    plan = EXPECTED["execution"]["plan_order"]
    assert [h.module_id for h in store.read().heads] == plan
    assert _receipt(positive).plan == tuple(plan)
    assert {h.status for h in store.read().heads} == {"restricted"}
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]
    _assert_head_equals_oracle(store, "positive")
    assert (
        len([f for f in store.head_module(_head(store, MODULE)).facts if "T4E." in f.table_id])
        == 256
    )


def test_a1_tool_use_is_the_oracle_sequence(positive: Closed) -> None:
    """One ok `read_inputs` (the lease's key tree, no quote), the oracle's searches and reads
    (financial page:4, legal-covenants page:1), no other ok call."""
    receipt = _receipt(positive)
    reads = [r for r in receipt.input_reads if r.binding.module_id == MODULE]
    assert len(reads) == 1
    assert reads[0].inputs_sha256 == hashlib.sha256(reads[0].body.encode()).hexdigest()
    keys = MANIFEST["tool_use"]["view_tree_draft"]["keys"]
    assert list(json.loads(reads[0].body)) == list(keys)
    view_tree.check("cp4c", "positive", reads[0].body)
    calls = [c for c in receipt.calls if c.binding.module_id == MODULE and c.status == "ok"]
    want = [c for c in SUBMISSIONS["cases"]["positive"]["tool_calls"] if c["tool"] != "read_inputs"]
    assert [(c.tool, c.arguments) for c in calls] == [(c["tool"], c["arguments"]) for c in want]
    store = _verify(positive)
    quotes = {
        c.quote for h in store.read().heads for f in store.head_module(h).facts for c in f.citations
    }
    assert quotes and not [q for q in quotes if q in reads[0].body]


def test_a1_the_settled_head_is_bound_to_its_tail_input(positive: Closed) -> None:
    store = _verify(positive)
    module = store.head_module(_head(store, MODULE))
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    text = store.payload(attempt.steps[0].payload_sha256)
    digest = cp4c.SCHEMAS[STEP].model_validate_json(text).content_hash()
    assert (module.inputs[-1].input_id, module.inputs[-1].sha256) == (cp4c.SUBMISSION_INPUT, digest)
    assert attempt.result_sha256 == _head(store, MODULE).result_sha256


def test_a1_first_run_confirms_the_t418_terms(positive: Closed) -> None:
    """Lease open question 8: the T4.18 ids are bound at run time. On the promoted CP-1 head the
    adapter reads the term loan SECURED and SENIOR at the cp1_references period."""
    store = _verify(positive)
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    cp1 = cp4c.cp4c_upstream(store=store, attempt=attempt).cp1
    rows = {
        r["label"].split(" · ")[2]: r
        for r in EXPECTED["cases"]["positive"]["cp1_references"]["rows"][2:]
    }
    for field, fact in (("secured_status", cp1.secured_status), ("seniority", cp1.seniority)):
        assert (fact.text, fact.period) == (rows[field]["text"], rows[field]["period"]), field


# --- A2 gap, A2b refused, A2c blocked / cp2g_blocked, A2d fixtures -----------------------------


def test_a2_gap_composes_honest_gaps_never_zero(gap: Closed) -> None:
    store = _verify(gap)
    _assert_head_equals_oracle(store, "gap")
    facts = {f.fact_id: f for f in store.head_module(_head(store, MODULE)).facts}
    unknown = [e for e in EXPECTED["cases"]["gap"]["facts"] if e["status"] != "known"]
    assert unknown and all(facts[e["fact_id"]].amount is None for e in unknown)


def test_a2b_refused_begin_for_cp1_and_no_later_module(
    refused: tuple[Closed, dict[str, Any]],
) -> None:
    closed, outcome = refused
    store = _verify(closed)
    want = EXPECTED["cases"]["refused"]
    assert [(r.module_id, r.reason) for r in _receipt(closed).refusals] == [
        (w["module_id"], w["reason"]) for w in want["refused_begins"]
    ]
    assert outcome["refusal"] == want["refusal"] == "cp1_not_authorized"
    assert [a.module_id for a in store.read().attempts] == want["attempts"]
    commands = [(c.row_id, c.text) for c in _head(store, "CP-0").commands]
    assert commands == [tuple(c) for c in want["cp0"]["T8_commands"]]


def test_a2c_blocked_run_leaves_a_blocked_head_and_a_verifying_receipt(blocked: Closed) -> None:
    store = _verify(blocked)
    expected = EXPECTED["cases"]["blocked"]
    head = _head(store, MODULE)
    module = store.head_module(head)
    assert head.status == expected["head"]["status"] == "blocked"
    assert module.tables == () and module.facts == ()
    attempts = [a for a in store.read().attempts if a.module_id == MODULE]
    assert [a.number for a in attempts] == [0, 1] and attempts[1].repair_of == attempts[0].ticket_id
    assert list(attempts[0].issues) == expected["attempt_0"]["limitations"]
    assert list(attempts[1].repair_issues) == expected["attempt_1"]["repair_issues"]
    assert list(module.limitations) == expected["attempt_1"]["limitations"]
    read = cp4c.cp4c_reader(store, head)
    assert (read.status, read.facts) == ("blocked", ())


def test_a2c_cp2g_blocked_refuses_the_cp4c_begin(
    cp2g_blocked: tuple[Closed, dict[str, Any]],
) -> None:
    closed, outcome = cp2g_blocked
    store = _verify(closed)
    want = EXPECTED["cases"]["cp2g_blocked"]
    assert _head(store, "CP-2G").status == "blocked"
    assert [(r.module_id, r.reason) for r in _receipt(closed).refusals] == [
        (MODULE, want["cp4c_begin"]["message"])
    ]
    assert outcome["refusal"] == want["refusal"] == "cp4c_blocked"
    assert not [a for a in store.read().attempts if a.module_id == MODULE]


def test_a2d_fixtures_are_composer_only_cases() -> None:
    """Fast: the three fixtures have no run (manifest); `test_method_cp4c.py` composes each one
    cell for cell against the oracle."""
    for fixture in stage1.FIXTURES:
        assert MANIFEST["cases"][fixture]["run"] is None
        assert fixture in stage1.CASES


# --- A3 refusals and tool use (forks of the waiting state) -------------------------------------


def _expected_issues(store: Execution, rid: str) -> list[str]:
    ids = _fig_ids(store)
    issues = [
        FACT_ID.sub(lambda m: ids[m[1]], i) for i in EXPECTED_REFUSALS[rid]["expected_issues"]
    ]
    # v08 cites identity page:1, outside the step's H1 scope: `read_pages` never returns it, so
    # the journal holds the validator issues and then the oracle's `unread_issues`
    return [*issues, *EXPECTED_REFUSALS[rid].get("unread_issues", ())]


def _refusal_text(workflow: OwnerWorkflow, rid: str, body: dict[str, Any]) -> str:
    refusal = REFUSALS[rid]
    if refusal.get("payload_text") is not None:
        return str(refusal["payload_text"])
    if refusal.get("bind_placeholders") is False:
        return json.dumps(refusal["payload"])
    return runs.bound_literal(workflow, refusal["payload"], body)


@pytest.mark.parametrize("rid", [r for r in RUN_LEVEL if REFUSALS[r].get("against") != "gap"])
def test_a3_each_refusal_is_journaled_with_the_oracle_issues(
    rid: str, waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    body = runs.read_view(workflow, "positive")
    outcome = workflow.submit_review(_refusal_text(workflow, rid, body))
    assert outcome["status"] == "invalid"
    assert list(outcome["issues"]) == _expected_issues(workflow._store, rid)


def test_a3_v11_is_journaled_against_the_gap_pack(tmp_path: Path) -> None:
    """v11 is stated against the gap case (`against: gap`): a fresh gap run up to CP-4C."""
    workflow = runs.ready("gap", tmp_path)
    body = runs.read_view(workflow, "gap")
    outcome = workflow.submit_review(_refusal_text(workflow, "v11", body))
    assert outcome["status"] == "invalid"
    assert list(outcome["issues"]) == _expected_issues(workflow._store, "v11")


@pytest.mark.parametrize("upstream_id", ["CP-1", "CP-2A", "CP-4", "CP-2G"])
def test_a3_a_new_upstream_head_between_read_and_submit_is_stale_binding(
    upstream_id: str, waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    """v24-v27 run level: the bound snapshot changes (a new head of one upstream) after the read;
    the next G1 call refuses `stale_binding`, consumes no attempt and journals no step."""
    workflow = clone_workflow(waiting, tmp_path)
    body = runs.read_view(workflow, "positive")
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    module = store.head_module(_head(store, upstream_id))
    changed = module.model_copy(update={"limitations": (*module.limitations, "A new head")})
    digest = store._store(changed.model_dump_json())
    heads = tuple(
        h.model_copy(update={"result_sha256": digest}) if h.module_id == upstream_id else h
        for h in snapshot.heads
    )
    store._write(snapshot.model_copy(update={"parent": snapshot.content_hash(), "heads": heads}))
    payload = runs.bound_literal(workflow, SUBMISSIONS["cases"]["positive"][STEP], body)
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(payload)
    assert caught.value.code == "stale_binding"
    attempts = [a for a in store.read().attempts if a.module_id == MODULE]
    assert [(a.number, a.status, a.steps) for a in attempts] == [(0, "pending", ())]


def test_a3_out_of_scope_tools_refused_and_submit_before_read_not_permitted(
    waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    for tool, arguments in (
        ("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1}),
        ("extract_statements", {"source_id": "financial", "first_page": 4, "last_page": 4}),
    ):
        call = workflow.invoke(tool, arguments)
        assert (call["status"], call["error_code"]) == ("refused", "not_permitted"), tool
    with pytest.raises(WorkflowError) as unread:
        workflow.submit_review(json.dumps(SUBMISSIONS["cases"]["positive"][STEP]))
    assert unread.value.code == "not_permitted"


def test_a3_an_unread_cited_page_is_refused(waiting: OwnerWorkflow, tmp_path: Path) -> None:
    """The read and the searches, but no `read_pages`: both cited pages are journaled unread."""
    workflow = clone_workflow(waiting, tmp_path)
    body = json.loads(workflow.read_inputs()["body"])
    outcome = workflow.submit_review(
        runs.bound_literal(workflow, SUBMISSIONS["cases"]["positive"][STEP], body)
    )
    assert outcome["status"] == "invalid"
    assert list(outcome["issues"]) == [
        f"{UNREAD_PAGE}: financial page:4",
        f"{UNREAD_PAGE}: legal-covenants page:1",
    ]


class _Fresh:
    """One fresh fork of the waiting state per hostile value (`model_text_failures`)."""

    waiting: OwnerWorkflow
    root: Path
    made = 0

    def __init__(self) -> None:
        _Fresh.made += 1
        self.workflow = clone_workflow(self.waiting, self.root / f"run{_Fresh.made}")

    def submit_review(self, text: str) -> dict[str, Any]:
        runs.read_view(self.workflow, "positive")
        outcome: dict[str, Any] = self.workflow.submit_review(text)
        return outcome


def test_a3_model_text_is_refused_or_verbatim_and_never_wedges(
    waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    """Round 3 item 2 and round 5 item 10 at run level (the validator form is fast)."""
    probe = clone_workflow(waiting, tmp_path / "probe")
    body = runs.read_view(probe, "positive")
    positive = runs.bound_literal(probe, SUBMISSIONS["cases"]["positive"][STEP], body)
    _Fresh.waiting, _Fresh.root = waiting, tmp_path
    schema = cp4c.RestructuringSubmission
    failures = model_text_failures(schema, positive, _Fresh, verbatim=CP4C_VERBATIM)
    assert failures == []


# --- A4 tamper (expected.json#tamper; the CP-DR `_forge` shape) ---------------------------------


def _forge(store_path: Path, receipt_path: Path) -> tuple[Execution, OwnerRunReceipt]:
    """The recipe of `expected.tamper`: edit the T4E.7.v03.value_break text, then rewrite every
    hash that names it (blob, snapshot, head, attempt, receipt, the settling submission record,
    the seal)."""
    tamper = EXPECTED["tamper"]
    store = Execution(store_path)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_bytes())
    snapshot = store.read()
    old = _head(store, MODULE)
    module = store.head_module(old)
    target = next(f for f in module.facts if f.fact_id == tamper["target_fact"])
    assert target.text == tamper["from"]
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": tamper["to"]}) if f.fact_id == target.fact_id else f
                for f in module.facts
            )
        }
    )
    new_sha = store._store(forged.model_dump_json())
    assert new_sha == forged.content_hash()
    assert head_of(forged, cp4c.QUALIFICATION).result_sha256 == new_sha
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


def test_a4_a_forged_value_break_reaches_the_probe_and_is_refused_there(
    positive: Closed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutil.copytree(positive[0], tmp_path / "forged")
    store, receipt = _forge(tmp_path / "forged", positive[1])
    ow._verify_audit(store, receipt)  # everything upstream of the probe passes on the copy ...
    reached: list[str] = []

    def spy(executed: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        reached.append(attempt.module_id)
        cp4c.probe(executed, snapshot, attempt)

    monkeypatch.setitem(ow._PROBES, MODULE, spy)
    with pytest.raises(WorkflowError) as caught:  # ... and the CP-4C probe refuses it
        ow.verify_owner_run_receipt(store, receipt)
    assert caught.value.code == "identity_mismatch"
    assert reached == [MODULE]


def test_a4_an_edited_step_output_is_caught_by_the_blob_hash(
    positive: Closed, tmp_path: Path
) -> None:
    shutil.copytree(positive[0], tmp_path / "store")
    store = Execution(tmp_path / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    blob = tmp_path / "store" / "blobs" / (attempt.steps[0].output_sha256 or "")
    blob.write_bytes(blob.read_bytes() + b" ")
    with pytest.raises(WorkflowError) as caught:
        ow.verify_owner_run_receipt(store, _receipt(positive))
    assert caught.value.code == "identity_mismatch"


# --- A6 consumption on the genuine heads ---------------------------------------------------------


def test_a6_cp4c_consumes_the_settled_cp2g_cp2a_and_cp4_heads(positive: Closed) -> None:
    store = _verify(positive)
    heads = {h.module_id: h for h in store.read().heads}
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]
    for item in attempt.inputs[1:]:
        head = heads[item.input_id]
        assert (item.sha256, item.status) == (head.result_sha256, head.status)
    module = store.head_module(heads[MODULE])
    mine = {f.fact_id: f for f in module.facts}
    theirs = {
        m: {f.fact_id: f for f in store.head_module(heads[m]).facts}
        for m in ("CP-2G", "CP-2A", "CP-4")
    }
    s = EXPECTED["cases"]["positive"]["cp2a_head"]["scenario"]
    read = cp2g.cp2g_reader(store, heads["CP-2G"])
    assert read.fact("T2H.3.d01.source").text == f"CP-2A T2B.1.{s}.ebitda_decline"
    assert mine["T4E.3.v02.cp2a_scenario"].text == theirs["CP-2A"][f"T2B.1.{s}.name"].text
    coordinates = {"table_id", "row_id", "field"}
    for name, source in (
        ("cp2g_references", "CP-2G"),
        ("cp2a_references", "CP-2A"),
        ("cp4_references", "CP-4"),
    ):
        table = next(t for t in module.tables if t.table_id == name)
        assert table.rows
        for row in table.rows:
            fid = row.fact_ids[0]
            assert mine[fid].model_dump(exclude=coordinates) == theirs[source][fid].model_dump(
                exclude=coordinates
            )
    # The composer's lineage over the same bound heads (a settled Fact stores none).
    upstream = cp4c.cp4c_upstream(store=store, attempt=attempt)
    text = store.payload(attempt.steps[0].payload_sha256)
    submission = cp4c.RestructuringSubmission.model_validate_json(text)
    cells = cp4c.compute(cp4c._inputs(store.pack(), submission, upstream)).cells
    lineage = {c.fact.fact_id: c.derives_from for c in cells}
    ebitda = {d for v in ("v01", "v02", "v03") for d in lineage[f"T4E.3.{v}.ebitda"]}
    assert ebitda == {"cp2g:T2H.4.b26.ebitda", "cp2g:T2H.4.d26.ebitda"}
    assert lineage["T4E.3.v01.first_break"] == ("cp2g:T2H.7.b01.base_first",)
    assert lineage["T4E.3.v02.ebitda_decline"] == (f"cp2a:T2B.1.{s}.ebitda_decline",)
    assert lineage["T4E.2.c01.facility"] == ("cp4:T4C.11.r01.facility",)
    assert lineage["T4E.2.c01.lender_protection"] == ("cp4:T4.13.rating.rating",)
    assert lineage["T4E.2.c01.additional_debt"] == ("cp4:T4.10.r02.conditions",)


# --- A7 rendering (bindings and spellings on the settled head; the G2 page is Stage 3) ----------


@pytest.mark.parametrize("fixture", ["positive", "gap"])
def test_a7_bindings_and_fp05_cells_on_the_settled_head(
    fixture: str, request: pytest.FixtureRequest
) -> None:
    closed: Closed = request.getfixturevalue(fixture)
    store = _verify(closed)
    module = store.head_module(_head(store, MODULE))
    view = View(
        run=store.pack().run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Restructuring fulcrum",
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
    assert validate_bindings(view, [m for m in SHIPPED_MAPS if m.module_id == MODULE]) == ()
    facts = {f.fact_id: f for f in module.facts}
    for block in EXPECTED["cases"][fixture]["FP05"]["blocks"].values():
        for tab in block["tabs"]:
            for row in tab["rows"]:
                for cell in row["cells"]:
                    _uc, state, text = fact_spelling(facts[cell["fact_id"]], "G1")
                    assert (state, text.replace("G1", "G#")) == (cell["state"], cell["shown"])


@pytest.mark.skip(reason="blocked on G2 (Stage 3): render_owner_slice and the DeliveryScope row")
def test_a7_g2_renders_the_two_recovery_blocks() -> None:
    """DeliveryScope(scope_id="cp4c-fp05-recovery", ...) renders recovery-by-class and
    value-allocation-claims populated, every other FP05 block idle (lease Rendered sections)."""


def test_driver_cases_are_the_manifest_runs() -> None:
    """Fast: the driver's cases are exactly the manifest cases that have a run."""
    runs_of = {c for c, v in MANIFEST["cases"].items() if v.get("run") is not None}
    assert runs_of == set(runs.CASES)
    assert set(runs.LITERAL) | {"refused"} == runs_of
