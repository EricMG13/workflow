"""CP-2G store runs (Stage 5 only): genuine CP-0 and CP-1 promotions, the frozen CP-1D and CP-2A
literals, then CP-2G, through the public `OwnerWorkflow` API, compared with
`cases/cp2g-owner/expected.json`. Each closed case is 11-26 minutes (module-scoped fixtures, one
job under the heavy-job lock). Written in Stage 2, never run there. Covers the lease Acceptance
section item by item:
- A1 positive: plan order and inputs, statuses, every T2H fact record, the reference tables,
  claims, own limitations, one ok `read_inputs` and no ok pack call, the tail input, and the
  first-run CP-1 readiness re-assertion (ruling 7);
- A2 gap; A2b refused; A2c blocked, cp2a_blocked and cp1d_blocked;
- A3 every refusal at run level (clones), the stale_binding clone per upstream, the tool-use
  refusals, model text at run level and the begin-refused outcome codes;
- A4 tamper (`expected.json#tamper`, the CP-DR `_forge` shape); A6 consumption on genuine heads;
  A7 the bindings and FP05 spellings on the settled head (the G2 page is Stage 3).
The fast forms over hand-seeded heads are `tests/test_connect_cp2g.py`. A5
(`test_owner_workflow.py`, `test_owner_s1a.py`, the CP-2A and CP-1D owner tests) is run as its
own files.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import cp2g_runs as runs
import pytest
import test_method_cp2g as stage1
import view_tree
from defect_classes import model_text_failures
from s1a_runs import clone_workflow
from test_connect_cp2g import CP2G_VERBATIM

from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import ModuleView, View
from deploy_vii.downstream_readiness import DownstreamReport, validate_downstream_review
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, head_of
from deploy_vii.report_view import fact_spelling
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.owners import cp2g
from deploy_workflow.workflow import WorkflowError

EXPECTED: dict[str, Any] = runs.oracle()["expected"]
SUBMISSIONS: dict[str, Any] = runs.oracle()["submissions"]
MODULE = "CP-2G"
STEP = runs.STEP
SYNTHETIC = "Synthetic case; not real issuer qualification"
Closed = tuple[Path, Path, None]
FIG = re.compile(r"\{\{FIG:([a-z0-9_]+)\|([^}]*)\}\}")
FACT_ID = re.compile(r"\{\{FACT_ID:([a-z_]+)\}\}")
REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
EXPECTED_REFUSALS = {r["id"]: r for r in EXPECTED["refusals"]}
RUN_LEVEL = [rid for rid in REFUSALS if rid not in ("v18", "v19", "v20")]


@pytest.fixture(scope="module")
def positive(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp2g_closed("positive", tmp_path_factory.mktemp("cp2g-positive"))


@pytest.fixture(scope="module")
def gap(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp2g_closed("gap", tmp_path_factory.mktemp("cp2g-gap"))


@pytest.fixture(scope="module")
def cp1d_blocked(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp2g_closed("cp1d_blocked", tmp_path_factory.mktemp("cp2g-cp1d-blocked"))


@pytest.fixture(scope="module")
def blocked(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp2g_closed("blocked", tmp_path_factory.mktemp("cp2g-blocked"))


@pytest.fixture(scope="module")
def refused(tmp_path_factory: pytest.TempPathFactory) -> tuple[Closed, dict[str, Any]]:
    """CP-0 only; the CP-0 submit's outcome (it carries the begin refusal) is kept."""
    root = tmp_path_factory.mktemp("cp2g-refused")
    workflow, pack = runs.start("refused", root)
    runs._driver("test_financial_workflow").read_sources(workflow, gap=True)
    outcome: dict[str, Any] = workflow.submit_review(runs.cp0_review(pack, "refused"))
    workflow.write_receipt(root / "owner-receipt.json")
    return (root / "store", root / "owner-receipt.json", None), outcome


@pytest.fixture(scope="module")
def cp2a_blocked(tmp_path_factory: pytest.TempPathFactory) -> tuple[Closed, dict[str, Any]]:
    """CP-2A r01 then v13 (its own oracle); the attempt-1 outcome (the CP-2G begin refusal)."""
    root = tmp_path_factory.mktemp("cp2g-cp2a-blocked")
    workflow, _ = runs.promoted("cp2a_blocked", root)
    cp2a_runs = runs._driver("cp2a_runs")
    refusals = {r["id"]: r for r in cp2a_runs.oracle()["submissions"]["refusals"]}
    outcome: dict[str, Any] = {}
    for rid in ("r01", "v13"):
        body = json.loads(workflow.read_inputs()["body"])
        outcome = workflow.submit_review(
            cp2a_runs.bound_literal(workflow, refusals[rid]["payload"], body)
        )
    workflow.write_receipt(root / "owner-receipt.json")
    return (root / "store", root / "owner-receipt.json", None), outcome


@pytest.fixture(scope="module")
def waiting(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    """Every upstream settled, CP-2G begun and untouched (positive; the slow part, built once)."""
    return runs.ready("positive", tmp_path_factory.mktemp("cp2g-ready"))


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
        if figure["source"] == "cp1d":
            out[name] = figure["fact_id"]
        else:
            label = f"{cp2g.LTM_COLUMN} · {figure['metric']}"
            out[name] = next(f.fact_id for f in cp1 if f.table_id == "T4.10" and f.label == label)
    return out


def _bind(text: str, ids: dict[str, str]) -> str:
    return FIG.sub(lambda m: "{" + ids[m[1]] + "|" + m[2] + "}", text)


def _assert_head_equals_oracle(store: Execution, case: str) -> None:
    """Every T2H fact record and spelling (a settled Fact stores no lineage: that is A6's), the
    tables, the reference tables, the claims (text with the run-time ids) and limitations."""
    want = EXPECTED["cases"][case]
    module = store.head_module(_head(store, MODULE))
    assert module.status == want["module_status"] == "restricted"
    own = [f for f in module.facts if f.table_id.startswith("T2H.")]
    assert [f.fact_id for f in own] == [e["fact_id"] for e in want["facts"]]
    for fact, e in zip(own, want["facts"], strict=True):
        cell = cp2g.Cell(fact, tuple(e.get("derives_from", ())), e["shown"])
        assert stage1._record(cell) == e, fact.fact_id
        _uc, _state, text = fact_spelling(fact, "G1")
        assert text.replace("G1", "G#") == e["shown"], fact.fact_id
    for table, e in zip(module.tables, want["tables"], strict=False):
        assert (table.table_id, table.title) == (e["table_id"], e["title"])
        assert [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] == [
            (r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]
        ]
    by_id = {f.fact_id: f for f in module.facts}
    for name in ("cp1_references", "cp2a_references", "cp1d_references"):
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


def test_a1_positive_heads_inputs_and_the_cp2g_head(positive: Closed) -> None:
    store = _verify(positive)
    plan = EXPECTED["execution"]["plan_order"]["positive"]
    assert [h.module_id for h in store.read().heads] == plan
    assert _receipt(positive).plan == tuple(plan)
    assert {h.status for h in store.read().heads} == {"restricted"}
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert [i.input_id for i in attempt.inputs] == EXPECTED["execution"]["inputs"]["positive"]
    _assert_head_equals_oracle(store, "positive")


def test_a1_one_ok_read_and_no_ok_pack_call_in_the_cp2g_step(positive: Closed) -> None:
    receipt = _receipt(positive)
    reads = [r for r in receipt.input_reads if r.binding.module_id == MODULE]
    calls = [c for c in receipt.calls if c.binding.module_id == MODULE]
    assert len(reads) == 1
    assert reads[0].inputs_sha256 == hashlib.sha256(reads[0].body.encode()).hexdigest()
    assert all(c.status != "ok" and c.error_code == "not_permitted" for c in calls)
    keys = runs.oracle()["manifest"]["tool_use"]["view_tree_draft"]["keys"]
    assert list(json.loads(reads[0].body)) == list(keys)
    view_tree.check("cp2g", "positive", reads[0].body)
    store = _verify(positive)
    quotes = {
        c.quote for h in store.read().heads for f in store.head_module(h).facts for c in f.citations
    }
    assert quotes and not [q for q in quotes if q in reads[0].body]


def test_a1_the_settled_head_is_bound_to_its_tail_input(positive: Closed) -> None:
    store = _verify(positive)
    module = store.head_module(_head(store, MODULE))
    assert module.inputs[-1].input_id == cp2g.SUBMISSION_INPUT
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert attempt.result_sha256 == _head(store, MODULE).result_sha256


def test_a1_first_run_cp1_readiness_reassertion(positive: Closed) -> None:
    """Ruling 7: on the bridge-pack CP-1 head the combined readiness literal validates and the
    CP-1D, CP-2A and CP-2G rows are `ready_with_limitations`. A mismatch goes to LEAD; the
    oracle is not edited."""
    store = _verify(positive)
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    step = next(s for s in attempt.steps if s.step_id == "readiness")
    report = DownstreamReport.model_validate_json(store.step_output(step.output_sha256 or ""))
    assert validate_downstream_review(report.inputs, report.review) == ()
    rows = {r.canonical_module: r.status for r in report.consumers}
    consumers = ("CP-1D", "CP-2A", "CP-2G")
    assert {m: rows[m] for m in consumers} == dict.fromkeys(consumers, "ready_with_limitations")
    assert EXPECTED["cp1_readiness"]["consumer_rows"]["CP-2G"]["status"] == rows["CP-2G"]


# --- A2 gap, A2b refused, A2c blocked / cp2a_blocked / cp1d_blocked ----------------------------


def test_a2_gap_composes_honest_gaps_never_zero(gap: Closed) -> None:
    store = _verify(gap)
    _assert_head_equals_oracle(store, "gap")
    assert "CP-1D" not in {h.module_id for h in store.read().heads}
    facts = {f.fact_id: f for f in store.head_module(_head(store, MODULE)).facts}
    for case in ("base", "down"):
        fact = facts[f"T2H.7.m01.{case}_first"]
        assert (fact.status, fact.text) == ("missing", None)
        assert fact.limitation == "Not calculable: minimum liquidity was not assessed"
    assert facts["T2H.6.a25.liquidity_headroom"].status == "not_applicable"


def test_a2b_refused_begin_for_cp1_and_no_cp2g_anywhere(
    refused: tuple[Closed, dict[str, Any]],
) -> None:
    closed, outcome = refused
    store = _verify(closed)
    want = EXPECTED["cases"]["refused"]
    assert [(r.module_id, r.reason) for r in _receipt(closed).refusals] == [
        (w["module_id"], w["reason"]) for w in want["refused_begins"]
    ]
    assert outcome["refusal"] == want["refusal"] == "cp1_not_authorized"
    assert not [a for a in store.read().attempts if a.module_id in ("CP-2A", MODULE)]
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
    read = cp2g.cp2g_reader(store, head)
    assert (read.status, read.facts) == ("blocked", ())


def test_a2c_blocked_attempt_1_limitations_equal_the_oracle(blocked: Closed) -> None:
    store = _verify(blocked)
    module = store.head_module(_head(store, MODULE))
    assert list(module.limitations) == EXPECTED["cases"]["blocked"]["attempt_1"]["limitations"]


def test_a2c_cp2a_blocked_refuses_the_cp2g_begin(
    cp2a_blocked: tuple[Closed, dict[str, Any]],
) -> None:
    closed, outcome = cp2a_blocked
    store = _verify(closed)
    want = EXPECTED["cases"]["cp2a_blocked"]
    assert _head(store, "CP-2A").status == "blocked"
    assert [(r.module_id, r.reason) for r in _receipt(closed).refusals] == [
        (MODULE, want["cp2g_begin"]["message"])
    ]
    assert outcome["refusal"] == want["refusal"] == "cp2g_blocked"
    assert not [a for a in store.read().attempts if a.module_id == MODULE]


def test_a2c_cp1d_blocked_binds_the_blocked_head_under_the_restricted_edge(
    cp1d_blocked: Closed,
) -> None:
    store = _verify(cp1d_blocked)
    assert _head(store, "CP-1D").status == "blocked"
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    assert next(i for i in attempt.inputs if i.input_id == "CP-1D").status == "blocked"
    _assert_head_equals_oracle(store, "cp1d_blocked")


# --- A3 refusals and tool use (forks of the waiting state) -------------------------------------


def _expected_issues(store: Execution, rid: str) -> list[str]:
    ids = _fig_ids(store)
    return [FACT_ID.sub(lambda m: ids[m[1]], i) for i in EXPECTED_REFUSALS[rid]["expected_issues"]]


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
    body = json.loads(workflow.read_inputs()["body"])
    outcome = workflow.submit_review(_refusal_text(workflow, rid, body))
    assert outcome["status"] == "invalid"
    assert list(outcome["issues"]) == _expected_issues(workflow._store, rid)


@pytest.mark.parametrize("upstream_id", ["CP-1", "CP-1D", "CP-2A"])
def test_a3_a_new_upstream_head_between_read_and_submit_is_stale_binding(
    upstream_id: str, waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    """v18-v20 run level: the bound snapshot changes (a new head of one upstream) after the read;
    the next G1 call refuses `stale_binding`, consumes no attempt and journals no step."""
    workflow = clone_workflow(waiting, tmp_path)
    body = json.loads(workflow.read_inputs()["body"])
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


def test_a3_pack_tools_refused_and_submit_before_read_not_permitted(
    waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    call = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert (call["status"], call["error_code"], call["body"]) == ("refused", "not_permitted", None)
    with pytest.raises(WorkflowError) as unread:
        workflow.submit_review(json.dumps(SUBMISSIONS["cases"]["positive"][STEP]))
    assert unread.value.code == "not_permitted"


def test_a3_unreplaced_figure_is_invalid(waiting: OwnerWorkflow, tmp_path: Path) -> None:
    workflow = clone_workflow(waiting, tmp_path)
    workflow.read_inputs()
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
        self.workflow.read_inputs()
        outcome: dict[str, Any] = self.workflow.submit_review(text)
        return outcome


def test_a3_model_text_is_refused_or_verbatim_and_never_wedges(
    waiting: OwnerWorkflow, tmp_path: Path
) -> None:
    """Round 3 item 2 and round 5 item 10 at run level (the validator form is fast)."""
    probe = clone_workflow(waiting, tmp_path / "probe")
    body = json.loads(probe.read_inputs()["body"])
    positive = runs.bound_literal(probe, SUBMISSIONS["cases"]["positive"][STEP], body)
    _Fresh.waiting, _Fresh.root = waiting, tmp_path
    failures = model_text_failures(cp2g.ForwardSubmission, positive, _Fresh, verbatim=CP2G_VERBATIM)
    assert failures == []


# --- A4 tamper (expected.json#tamper; the CP-DR `_forge` shape) ---------------------------------


def _forge(store_path: Path, receipt_path: Path) -> tuple[Execution, OwnerRunReceipt]:
    """The recipe of `expected.tamper`: edit the T2H.7.b03.down_first text, then rewrite every
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
    assert head_of(forged, cp2g.QUALIFICATION).result_sha256 == new_sha
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
        cp2g.probe(executed, snapshot, attempt)

    monkeypatch.setitem(ow._PROBES, MODULE, spy)
    with pytest.raises(WorkflowError) as caught:  # ... and the CP-2G probe refuses it
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


def test_a6_cp2g_consumes_the_settled_cp2a_and_cp1d_heads(positive: Closed) -> None:
    store = _verify(positive)
    heads = {h.module_id: h for h in store.read().heads}
    attempt = next(a for a in store.read().attempts if a.module_id == MODULE)
    for item in attempt.inputs[1:]:
        head = heads[item.input_id]
        assert (item.sha256, item.status) == (head.result_sha256, head.status)
    module = store.head_module(heads[MODULE])
    mine = {f.fact_id: f for f in module.facts}
    cp2a_facts = {f.fact_id: f for f in store.head_module(heads["CP-2A"]).facts}
    cp1d_facts = {f.fact_id: f for f in store.head_module(heads["CP-1D"]).facts}
    s = EXPECTED["cases"]["positive"]["cp2a_head"]["downside_scenario"]
    read = cp2g.cp2g_reader(store, heads[MODULE])
    assert read.fact("T2H.3.d01.source").text == f"CP-2A T2B.1.{s}.ebitda_decline"
    assert read.fact("T2H.3.d02.source").text == f"CP-2A T2B.1.{s}.interest_increase"
    assert mine["T2H.3.d01.fy1"].amount == cp2a_facts[f"T2B.1.{s}.ebitda_decline"].amount
    supported = cp1d_facts["T1D.3.supported.value"].amount
    assert mine["T2H.2.ebitda_supported.value"].amount == supported
    coordinates = {"table_id", "row_id", "field"}
    for name, theirs in (("cp2a_references", cp2a_facts), ("cp1d_references", cp1d_facts)):
        table = next(t for t in module.tables if t.table_id == name)
        for row in table.rows:
            fid = row.fact_ids[0]
            assert mine[fid].model_dump(exclude=coordinates) == theirs[fid].model_dump(
                exclude=coordinates
            )
    # The composer's lineage over the same bound heads (a settled Fact stores none).
    upstream = cp2g.cp2g_upstream(store=store, attempt=attempt)
    text = store.payload(attempt.steps[0].payload_sha256)
    submission = cp2g.ForwardSubmission.model_validate_json(text)
    cells = cp2g.compute(cp2g._inputs(store.pack(), submission, upstream)).cells
    lineage = {c.fact.fact_id: c.derives_from for c in cells}
    for fid in (f"T2H.4.d2{n}.ebitda" for n in (6, 7, 8)):
        assert f"cp2a:T2B.1.{s}.ebitda_decline" in lineage[fid]
    via_cp1d = [fid for fid, d in lineage.items() if any(x.startswith("cp1d:T1D.") for x in d)]
    assert len(via_cp1d) == 6


# --- A7 rendering (bindings and spellings on the settled head; the G2 page is Stage 3) ----------


@pytest.mark.parametrize("fixture", ["positive", "gap", "cp1d_blocked"])
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
                title="Forward credit model",
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
def test_a7_g2_renders_the_two_forward_blocks() -> None:
    """DeliveryScope(scope_id="cp2g-fp05-forward", ...) renders forward-credit-path and
    forward-breakpoints populated, every other FP05 block idle (lease Rendered sections)."""


def test_bridge_cases_are_the_runs_that_request_cp1d() -> None:
    """Fast: the driver's bridge cases are exactly the runs that request CP-1D."""
    cases = runs.oracle()["manifest"]["cases"]
    runs_of = {c: v["run"] for c, v in cases.items() if v.get("run") is not None}
    assert set(runs_of) == set(runs.CASES)
    assert set(runs.BRIDGE) == {c for c, r in runs_of.items() if "CP-1D" in r["requested_modules"]}
