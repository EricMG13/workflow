"""CP-2H store runs (Stage 5 only): genuine CP-0 and CP-1 promotions, the frozen CP-2A and CP-2G
literals, then CP-2H, through the public `OwnerWorkflow` API, compared with
`cases/cp2h-owner/expected.json`. Each closed case is 11-26 minutes (module-scoped fixtures, one
job under the heavy-job lock). Written in Stage 2, never run there. Covers the lease Acceptance
section item by item:
- A1 positive: plan order and inputs, statuses, every T2R fact record, the reference tables,
  claims, own limitations, one ok `read_inputs` then ok `read_pages` covering every cited page,
  the tail input, and the first-run CP-1 readiness re-assertion (open question 2);
- A2 gap; A2b refused; A2c blocked and cp2g_blocked;
- A3 every run-level refusal (clones), the stale_binding clone per upstream, the tool-use
  refusals t01-t03 and model text at run level;
- A4 tamper (`expected.json#tamper`, the CP-DR `_forge` shape); A6 consumption (D3) on the
  genuine CP-2G head; A7 the bindings and FP05 spellings on the settled head (the G2 page is
  Stage 3).
The fast forms over hand-seeded heads are `tests/test_connect_cp2h.py`. A5
(`test_owner_workflow.py`, `test_owner_s1a.py`, the CP-2A and CP-2G owner tests) is run as its
own files.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import cp2h_runs as runs
import pytest
import test_method_cp2h as stage1
from defect_classes import model_text_failures
from s1a_runs import clone_workflow
from test_connect_cp2h import CP2H_VERBATIM

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Citation, ModuleView, View
from deploy_vii.downstream_readiness import DownstreamReport, validate_downstream_review
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, head_of
from deploy_vii.live.tools import cited_locators
from deploy_vii.report_view import fact_spelling
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.owners import cp2g, cp2h
from deploy_workflow.workflow import WorkflowError

EXPECTED: dict[str, Any] = runs.oracle()["expected"]
SUBMISSIONS: dict[str, Any] = runs.oracle()["submissions"]
MODULE = "CP-2H"
STEP = runs.STEP
SYNTHETIC = "Synthetic case; not real issuer qualification"
Closed = tuple[Path, Path, None]
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\|([^}]*)\}\}")
REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
EXPECTED_REFUSALS = {r["id"]: r for r in EXPECTED["refusals"]}
TOOL_REFUSALS = {t["id"]: t for t in SUBMISSIONS["tool_refusals"]}
RUN_LEVEL = [rid for rid, r in REFUSALS.items() if not r.get("composer_only")]


@pytest.fixture(scope="module")
def positive(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp2h_closed("positive", tmp_path_factory.mktemp("cp2h-positive"))


@pytest.fixture(scope="module")
def gap(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp2h_closed("gap", tmp_path_factory.mktemp("cp2h-gap"))


@pytest.fixture(scope="module")
def blocked(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp2h_closed("blocked", tmp_path_factory.mktemp("cp2h-blocked"))


@pytest.fixture(scope="module")
def refused(tmp_path_factory: pytest.TempPathFactory) -> tuple[Closed, dict[str, Any]]:
    """CP-0 only; the CP-0 submit's outcome (it carries the CP-1 begin refusal) is kept."""
    root = tmp_path_factory.mktemp("cp2h-refused")
    workflow, outcome = runs.promoted("refused", root)
    workflow.write_receipt(root / "owner-receipt.json")
    return (root / "store", root / "owner-receipt.json", None), outcome


@pytest.fixture(scope="module")
def cp2g_blocked(tmp_path_factory: pytest.TempPathFactory) -> tuple[Closed, dict[str, Any]]:
    """CP-2G r01 then v13 (its own oracle); the attempt-1 outcome (the CP-2H begin refusal)."""
    root = tmp_path_factory.mktemp("cp2h-cp2g-blocked")
    workflow, _ = runs.promoted("cp2g_blocked", root)
    runs.drive_cp2a(workflow)
    outcome = runs.drive_cp2g_blocked(workflow)
    workflow.write_receipt(root / "owner-receipt.json")
    return (root / "store", root / "owner-receipt.json", None), outcome


@pytest.fixture(scope="module")
def waiting(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    """Every upstream settled, CP-2H begun and untouched (positive; the slow part, built once)."""
    return runs.ready("positive", tmp_path_factory.mktemp("cp2h-ready"))


def _receipt(closed: Closed) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json(closed[1].read_bytes())


def _verify(closed: Closed) -> Execution:
    store = Execution(closed[0])
    ow.verify_owner_run_receipt(store, _receipt(closed))
    return store


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _fig_ids(store: Execution) -> dict[str, str]:
    """FIG name -> the fact id bound at run time (`manifest.json cp1_fact_selection_rule`)."""
    cp1 = store.head_module(_head(store, "CP-1")).facts
    return {
        name: next(
            f.fact_id
            for f in cp1
            if f.table_id == "T4.10" and f.label == f"{cp2h.LTM_COLUMN} · {figure['metric']}"
        )
        for name, figure in SUBMISSIONS["figures"].items()
    }


def _bind(text: str, ids: dict[str, str]) -> str:
    return FIG.sub(lambda m: "{" + ids[m[1]] + "|" + m[2] + "}", text)


def _tree_bytes(path: Path) -> dict[str, str]:
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


def _assert_head_equals_oracle(store: Execution, case: str) -> None:
    """Every T2R fact record and spelling (lineage is A6's; the upstream citations appended at run
    time follow the oracle's own), the tables, the reference tables, the claims (text with the
    run-time ids) and the limitations."""
    want = EXPECTED["cases"][case]
    module = store.head_module(_head(store, MODULE))
    assert module.status == "restricted"
    own = [f for f in module.facts if f.table_id.startswith("T2R.")]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    for fact, e in zip(own, want["facts"], strict=True):
        cites = tuple(Citation.model_validate(c) for c in e.get("citations", ()))
        assert fact.citations[: len(cites)] == cites, fact.fact_id
        bare = fact.model_copy(update={"citations": cites})
        stage1._assert_cell(cp2h.Cell(bare, tuple(e.get("derives_from", ())), e["shown"]), e)
        _uc, _state, text = fact_spelling(fact, "G1")
        assert e["shown"] is None or text.replace("G1", "G#") == e["shown"], fact.fact_id
    d8 = EXPECTED["d8_table_ids"]
    assert [t.table_id for t in module.tables] == [
        *d8["cp2h_table_ids"],
        *d8["module_tables_besides"],
    ]
    for table, e in zip(module.tables, want["tables"], strict=False):
        assert (table.table_id, table.title) == (e["table_id"], e["title"])
        assert [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] == [
            (r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]
        ]
    by_id = {f.fact_id: f for f in module.facts}
    for name in ("cp1_references", "cp2g_references"):
        table = next(t for t in module.tables if t.table_id == name)
        rows = want[name]["rows"]
        assert [(r.row_id, r.label) for r in table.rows] == [
            (r["row_id"], r["label"]) for r in rows
        ]
        for row, e in zip(table.rows, rows, strict=True):
            fact = by_id[row.fact_ids[0]]
            exact = None if fact.amount is None else cp2h.exact_text(fact.amount)
            assert (fact.status, exact) == (e["status"], e["amount_exact"]), row.row_id
    ids = _fig_ids(store)
    assert [
        (c.claim_id, c.text, [x.model_dump() for x in c.citations], c.limitation)
        for c in module.claims
    ] == [
        (c["claim_id"], _bind(c["text"], ids), c["citations"], c["limitation"])
        for c in want["claims"]
    ]
    assert list(module.limitations) == [*want["own_limitations"], SYNTHETIC]


# --- A1 positive ------------------------------------------------------------------------------


def test_a1_positive_heads_inputs_and_the_cp2h_head(positive: Closed) -> None:
    store = _verify(positive)
    plan = EXPECTED["execution"]["plan_order"]["positive"]
    assert [h.module_id for h in store.read().heads] == plan
    assert _receipt(positive).plan == tuple(plan)
    assert {h.status for h in store.read().heads} == {"restricted"}
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]["positive"]
    _assert_head_equals_oracle(store, "positive")


def test_a1_one_read_then_the_cited_pages_in_the_cp2h_step(positive: Closed) -> None:
    receipt = _receipt(positive)
    reads = [r for r in receipt.input_reads if r.binding.module_id == MODULE]
    calls = [c for c in receipt.calls if c.binding.module_id == MODULE]
    assert len(reads) == 1
    assert reads[0].inputs_sha256 == hashlib.sha256(reads[0].body.encode()).hexdigest()
    keys = runs.oracle()["manifest"]["tool_use"]["view_tree_draft"]["keys"]
    assert list(json.loads(reads[0].body)) == list(keys)
    literal = [
        c for c in SUBMISSIONS["cases"]["positive"]["tool_calls"] if c["tool"] != "read_inputs"
    ]
    assert [(c.tool, c.arguments, c.status) for c in calls] == [
        (c["tool"], c["arguments"], "ok") for c in literal
    ]
    store = _verify(positive)
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    cited = cited_locators(store.payload(attempt.steps[0].payload_sha256))
    read = {
        ("ratings", f"page:{n}")
        for c in calls
        for n in range(c.arguments["first_page"], c.arguments["last_page"] + 1)
    }
    assert cited and cited <= read
    quotes = {
        c["quote"] for v in SUBMISSIONS["cases"]["positive"][STEP]["views"] for c in v["evidence"]
    }
    assert quotes and not [q for q in quotes if q in reads[0].body]


def test_a1_the_settled_head_is_bound_to_its_tail_input(positive: Closed) -> None:
    store = _verify(positive)
    module = store.head_module(_head(store, MODULE))
    assert module.inputs[-1].input_id == cp2h.SUBMISSION_INPUT
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert attempt.result_sha256 == _head(store, MODULE).result_sha256
    assert _head(store, MODULE).qualification == cp2h.QUALIFICATION


def test_a1_first_run_cp1_readiness_reassertion(positive: Closed) -> None:
    """Open question 2: on the ratings-source pack the combined readiness literal validates and
    the CP-2H row is `ready_with_limitations`. A mismatch goes to LEAD; the oracle is not edited."""
    store = _verify(positive)
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    step = next(s for s in attempt.steps if s.step_id == "readiness")
    report = DownstreamReport.model_validate_json(store.step_output(step.output_sha256 or ""))
    assert validate_downstream_review(report.inputs, report.review) == ()
    rows = {r.canonical_module: r.status for r in report.consumers}
    assert rows[MODULE] == EXPECTED["cp1_readiness"]["consumer_rows"][MODULE]["status"]


def test_a1_verifying_writes_nothing(positive: Closed) -> None:
    before = _tree_bytes(positive[0])
    _verify(positive)
    assert _tree_bytes(positive[0]) == before


# --- A2 gap, A2b refused, A2c blocked / cp2g_blocked ---------------------------------------------


def test_a2_gap_composes_honest_gaps_never_zero(gap: Closed) -> None:
    store = _verify(gap)
    _assert_head_equals_oracle(store, "gap")
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]["gap"]
    facts = {f.fact_id: f for f in store.head_module(_head(store, MODULE)).facts}
    unstated = [
        f
        for f in facts.values()
        if (f.table_id, f.field, f.status) == ("T2R.3", "threshold", "missing")
    ]
    assert unstated and all(f.amount is None for f in unstated)
    for threshold in unstated:  # an unstated threshold is a gap downstream, never a zero
        headroom = facts[f"T2R.4.{threshold.row_id}.headroom"]
        assert (headroom.status, headroom.amount) == ("missing", None)


def test_a2b_refused_begin_for_cp1_and_no_cp2h_anywhere(
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
    assert [h.module_id for h in store.read().heads] == want["heads"]
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


def test_a2c_cp2g_blocked_refuses_the_cp2h_begin(
    cp2g_blocked: tuple[Closed, dict[str, Any]],
) -> None:
    closed, outcome = cp2g_blocked
    store = _verify(closed)
    want = EXPECTED["cases"]["cp2g_blocked"]
    assert _head(store, "CP-2G").status == "blocked"
    assert [(r.module_id, r.reason) for r in _receipt(closed).refusals] == [
        (MODULE, want["cp2h_begin"]["message"])
    ]
    assert outcome["refusal"] == want["refusal"] == "cp2h_blocked"
    assert not [a for a in store.read().attempts if a.module_id == MODULE]


# --- A3 refusals and tool use (forks of the waiting state) -------------------------------------


def _refusal_text(workflow: OwnerWorkflow, rid: str, body: dict[str, Any]) -> str:
    refusal = REFUSALS[rid]
    if refusal.get("payload_text") is not None:
        return str(refusal["payload_text"])
    if refusal.get("bind_placeholders") is False:
        return json.dumps(refusal["payload"])
    return runs.bound_literal(workflow, refusal["payload"], body)


@pytest.mark.parametrize("rid", RUN_LEVEL)
def test_a3_each_refusal_is_journaled_with_the_oracle_issues(
    rid: str, waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    body = runs.read_view_and_pages(workflow)
    outcome = workflow.submit_review(_refusal_text(workflow, rid, body))
    assert outcome["status"] == "invalid"
    want = EXPECTED_REFUSALS[rid]
    if rid == "v16":
        assert len(outcome["issues"]) == 1
        assert outcome["issues"][0].startswith(want["issue_prefix"])
    else:
        assert list(outcome["issues"]) == want["expected_issues"]


@pytest.mark.parametrize("upstream_id", ["CP-1", "CP-2G"])
def test_a3_a_new_upstream_head_between_read_and_submit_is_stale_binding(
    upstream_id: str, waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    """v17/v18 run level: the bound snapshot changes (a new head of one upstream) after the
    read; the next G1 call refuses `stale_binding`, consumes no attempt and journals no step."""
    workflow = clone_workflow(waiting, tmp_path)
    body = runs.read_view_and_pages(workflow)
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


def test_a3_t01_a_cited_page_not_read_is_an_invalid_attempt_then_the_repair(
    waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    payload = runs.bound_literal(workflow, SUBMISSIONS["cases"]["positive"][STEP], body)
    outcome = workflow.submit_review(payload)
    assert outcome["status"] == "invalid"
    assert list(outcome["issues"]) == TOOL_REFUSALS["t01"]["expected_issues"]
    runs.read_view_and_pages(workflow)
    assert workflow.submit_review(payload)["status"] == "valid"
    attempts = [a for a in workflow._store.read().attempts if a.module_id == MODULE]
    assert [a.number for a in attempts] == [0, 1] and attempts[1].repair_of == attempts[0].ticket_id


def test_a3_t02_a_non_pack_invoke_is_a_refused_receipt(
    waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    before = workflow._store.read()
    t02 = TOOL_REFUSALS["t02"]
    call = workflow.invoke(t02["call"]["tool"], t02["call"]["arguments"])
    assert (call["status"], call["error_code"]) == (
        t02["expected_receipt"]["status"],
        t02["expected_receipt"]["reason"],
    )
    assert workflow._store.read() == before


def test_a3_t03_submit_before_read_inputs_is_not_permitted(
    waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    before = _tree_bytes(tmp_path / "store")
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(json.dumps(SUBMISSIONS["cases"]["positive"][STEP]))
    assert caught.value.code == TOOL_REFUSALS["t03"]["expected_error"]
    assert _tree_bytes(tmp_path / "store") == before


def test_a3_unreplaced_figure_is_invalid(waiting: OwnerWorkflow, tmp_path: Path) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    runs.read_view_and_pages(workflow)
    outcome = workflow.submit_review(json.dumps(SUBMISSIONS["cases"]["positive"][STEP]))
    assert outcome["status"] == "invalid"
    assert any("Malformed run text" in issue for issue in outcome["issues"]), outcome["issues"]


class _Fresh:
    """One fresh fork of the waiting state per hostile value (`model_text_failures`)."""

    waiting: OwnerWorkflow
    root: Path
    made = 0

    def __init__(self) -> None:
        _Fresh.made += 1
        self.workflow = clone_workflow(self.waiting, self.root / f"run{_Fresh.made}")

    def submit_review(self, text: str) -> dict[str, Any]:
        runs.read_view_and_pages(self.workflow)
        outcome: dict[str, Any] = self.workflow.submit_review(text)
        return outcome


def test_a3_model_text_is_refused_and_never_wedges(waiting: OwnerWorkflow, tmp_path: Path) -> None:
    """Round 3 item 2 and round 5 item 10 at run level (the validator form is fast)."""
    probe = clone_workflow(waiting, tmp_path / "probe")
    body = runs.read_view_and_pages(probe)
    positive = runs.bound_literal(probe, SUBMISSIONS["cases"]["positive"][STEP], body)
    _Fresh.waiting, _Fresh.root = waiting, tmp_path
    failures = model_text_failures(cp2h.TriggerSubmission, positive, _Fresh, verbatim=CP2H_VERBATIM)
    assert failures == []


# --- A4 tamper (expected.json#tamper; the CP-DR `_forge` shape) ---------------------------------


def _forge(store_path: Path, receipt_path: Path) -> tuple[Execution, OwnerRunReceipt]:
    """The recipe of `expected.tamper`: edit the T2R.6.t04.down_first text, then rewrite every
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
    assert head_of(forged, cp2h.QUALIFICATION).result_sha256 == new_sha
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


def test_a4_a_forged_first_year_reaches_the_probe_and_is_refused_there(
    positive: Closed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutil.copytree(positive[0], tmp_path / "forged")
    store, receipt = _forge(tmp_path / "forged", positive[1])
    ow._verify_audit(store, receipt)  # everything upstream of the probe passes on the copy ...
    reached: list[str] = []

    def spy(executed: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        reached.append(attempt.module_id)
        cp2h.probe(executed, snapshot, attempt)

    monkeypatch.setitem(ow._PROBES, MODULE, spy)
    with pytest.raises(WorkflowError) as caught:  # ... and the CP-2H probe refuses it
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


# --- A6 consumption (D3) on the genuine heads ----------------------------------------------------


def test_a6_cp2h_consumes_the_settled_cp2g_head(positive: Closed) -> None:
    """expected.json execution.consumption (a)-(d) on the closed run."""
    store = _verify(positive)
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    attempt = next(a for a in snapshot.attempts if a.module_id == MODULE)
    # (a), (b)
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]["positive"]
    assert attempt.inputs[0].sha256 == snapshot.pack_sha256
    for item in attempt.inputs[1:]:
        assert (item.sha256, item.status) == (
            heads[item.input_id].result_sha256,
            heads[item.input_id].status,
        )
    # (c) the composer's lineage over the same bound heads (a settled Fact stores none)
    upstream = cp2h.cp2h_upstream(store=store, attempt=attempt)
    submission = cp2h.TriggerSubmission.model_validate_json(
        store.payload(attempt.steps[0].payload_sha256)
    )
    cells = cp2h.compute(cp2h._inputs(store.pack(), submission, upstream)).cells
    lineage = {c.fact.fact_id: c.derives_from for c in cells}
    want = EXPECTED["cases"]["positive"]["facts"]
    assert lineage == {f["fact_id"]: tuple(f.get("derives_from", ())) for f in want}

    def reads(fid: str) -> list[str]:
        return [r.removeprefix("cp2g:") for r in lineage[fid] if r.startswith("cp2g:T2H.6.")]

    actual = [f for f in lineage if f.startswith("T2R.4.") and f.endswith(".actual")]
    yearly = [f for f in lineage if f.startswith("T2R.5.") and f[-2:] in ("y1", "y2", "y3")]
    first = [f for f in lineage if f.startswith("T2R.6.") and len(reads(f)) == 3]
    assert (len(actual), len(yearly), len(first)) == (5, 30, 10)
    # (d) every settled value and copy is the CP-2G head's own
    read = cp2g.cp2g_reader(store, heads["CP-2G"])
    theirs = {f.fact_id: f for f in read.facts}
    module = store.head_module(heads[MODULE])
    mine = {f.fact_id: f for f in module.facts}
    for fid in actual:
        (ref,) = reads(fid)
        assert (mine[fid].status, mine[fid].amount) == (theirs[ref].status, theirs[ref].amount)
    coordinates = {"table_id", "row_id", "field"}
    table = next(t for t in module.tables if t.table_id == "cp2g_references")
    copied = [row.fact_ids[0] for row in table.rows]
    assert sorted(copied) == EXPECTED["cases"]["positive"]["cp2g_head"]["facts_read"]
    for fid in copied:
        assert mine[fid].model_dump(exclude=coordinates) == theirs[fid].model_dump(
            exclude=coordinates
        )


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
                title="Rating triggers",
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
def test_a7_g2_renders_the_rating_triggers_block() -> None:
    """DeliveryScope(scope_id="cp2h-fp05-ratings", pathway="distressed_restructuring",
    requested_modules=("CP-2H",), sections=("rating-triggers",), rails=("evidence","limitations"))
    renders rating-triggers populated; the other FP05 blocks come from their own heads."""


def test_driver_cases_are_the_manifest_runs() -> None:
    """Fast: the driver's cases are exactly the manifest cases that have a run."""
    cases = runs.oracle()["manifest"]["cases"]
    assert set(runs.CASES) == {c for c, v in cases.items() if v.get("run") is not None}
    assert set(runs.LITERALS) == set(runs.CASES) - {"refused"}
