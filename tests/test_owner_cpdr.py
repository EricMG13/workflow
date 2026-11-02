"""O7b-1c S2b: the CP-DR LOCAL closed run, through the public `OwnerWorkflow` API.

Answer key: `cases/cpdr-research-owner/expected.json` (frozen; read at test time, never edited).
One genuine run (CP-0 and CP-1 promoted, then the `brief` and `research` steps) is built once; the
tests compare what it left with the key:

- `#cases/positive/{cp_dr_head_status_expected,facts}` and the table order TDR.1-3 (the head);
- `#cases/positive/brief/template_file` and `#brief/{question_ids,kinds,receivers,focus_modules}`
  (`research/brief.json`, a defaults-only brief);
- `#cases/positive/dossier/{template_text,dossier_sha256_rule,head_hash_rule}` (`research/dossier.md`
  and the hashes `run.json` records);
- `#refusals/anchors/blocked_cp0` (a blocked CP-0 head), `#refusals/research/fence_terminator`.

S2c adds the remaining owner-level cases. The first fixture is slow (about two minutes); the tests
that follow it reuse its store.
"""

import ast
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import cpdr_runs as runs
import pytest
from cpdr_s1_support import ResearchCase

from deploy_vii import registry
from deploy_vii.contracts import validate_tables
from deploy_vii.execution import Execution, Head
from deploy_workflow import owner_workflow
from deploy_workflow import run_pathway as rp
from deploy_workflow.model.loop import StepStopped
from deploy_workflow.model.redact import Redactor
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt
from deploy_workflow.owners import cpdr
from deploy_workflow.prompts import rules
from deploy_workflow.research import evidence
from deploy_workflow.research.anchors import check_anchors
from deploy_workflow.research.contracts import BriefInvalid, CpDrNotAnchored
from deploy_workflow.research.dossier import render_dossier
from deploy_workflow.research.intake import RefusedItem, write_rejected
from deploy_workflow.run_inputs import check_arguments
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]
BRIEF_MARKER = "{{BRIEF_SHA256}}"
FORGED = "TDR.3.total.answered"  # the fact the forgery test changes
FACT_FIELDS = (
    "fact_id",
    "table_id",
    "row_id",
    "field",
    "label",
    "text",
    "amount",
    "status",
    "unit",
    "period",
)


@dataclass(frozen=True)
class Closed:
    root: Path
    store: Path
    receipt: Path
    run: runs.ClosedRun

    def execution(self) -> Execution:
        return Execution(self.store)

    def head(self, module_id: str) -> Head:
        return next(h for h in self.execution().read().heads if h.module_id == module_id)


@pytest.fixture(scope="module")
def key() -> dict[str, Any]:
    expected: dict[str, Any] = runs.oracle()["expected"]
    return expected


@pytest.fixture(scope="module")
def closed(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    """The positive case, closed and finished as `run_pathway` finishes a run: CP-0, CP-1 and
    CP-DR settled, `owner-run.json` sealed, `run.json` written. Shared with the run-level tests."""
    made = runs.closed_run("positive", tmp_path_factory)
    return Closed(made.root, made.root / "execution", made.root / "owner-run.json", made)


sha, brief_file = runs.sha, runs.brief_file


# --- the positive closed run --------------------------------------------------------------------


def test_closed_run_positive(closed: Closed, key: dict[str, Any]) -> None:
    """The head settles at the key's status with TDR.1-3 in order, its facts are the key's, the
    tables lay out over them, and the sealed receipt verifies from the store and the record."""
    want = key["cases"]["positive"]
    head = closed.head("CP-DR")
    assert head.status == want["cp_dr_head_status_expected"] == "restricted"
    module = closed.execution().head_module(head)
    assert [table.table_id for table in module.tables] == ["TDR.1", "TDR.2", "TDR.3"]
    validate_tables(module.tables, module.facts)
    by_id = {fact.fact_id: fact for fact in module.facts}
    assert sorted(by_id) == sorted(f["fact_id"] for f in want["facts"])
    for wanted in want["facts"]:
        fact = by_id[wanted["fact_id"]]
        got = {n: None if (v := getattr(fact, n)) is None else str(v) for n in FACT_FIELDS}
        assert got == {n: wanted.get(n) for n in FACT_FIELDS}, fact.fact_id
        assert fact.limitation == wanted.get("limitation"), fact.fact_id
    receipt = OwnerRunReceipt.model_validate_json(closed.receipt.read_bytes())
    verify_owner_run_receipt(closed.execution(), receipt)


def test_the_receipt_plan_is_the_registry_plan_and_the_cpdr_attempt_binds_cp1(
    closed: Closed, key: dict[str, Any]
) -> None:
    """Plan 4 rows 17 and 21: the sealed receipt's plan is the key's registry order, and CP-DR's
    attempt bound CP-1 (lineage) at the CP-1 head's hash."""
    receipt = OwnerRunReceipt.model_validate_json(closed.receipt.read_bytes())
    want = key["registry_after_o7b1"]["plan_order_for_requested_CP-1_CP-DR"]
    assert list(receipt.plan) == want == list(registry.plan(("CP-1", "CP-DR")))
    attempt = next(a for a in closed.execution().read().attempts if a.module_id == "CP-DR")
    bound = {item.input_id: item for item in attempt.inputs}
    assert bound["CP-1"].sha256 == closed.head("CP-1").result_sha256
    assert bound["CP-0"].sha256 == closed.head("CP-0").result_sha256


def test_the_brief_file_is_the_key_template(closed: Closed, key: dict[str, Any]) -> None:
    template = key["cases"]["positive"]["brief"]["template_file"]
    want, digest = brief_file(
        template, closed.head("CP-0").result_sha256, closed.head("CP-1").result_sha256
    )
    written = (closed.root / "research" / "brief.json").read_bytes()
    assert written == want.encode("utf-8")
    assert json.loads(written)["brief_sha256"] == digest


def test_a_defaults_only_brief_gives_the_keys_eight_questions(
    closed: Closed, key: dict[str, Any]
) -> None:
    brief = json.loads((closed.root / "research" / "brief.json").read_text(encoding="utf-8"))
    questions = brief["questions"]
    wanted = key["brief"]
    assert [q["question_id"] for q in questions] == wanted["question_ids"]
    assert [q["kind"] for q in questions] == wanted["kinds"]
    assert {q["question_id"]: q["receivers"] for q in questions} == wanted["receivers"]
    assert {q["question_id"]: q["focus_module"] for q in questions} == wanted["focus_modules"]


def test_the_dossier_is_the_key_template_and_its_hashes_are_recorded(
    closed: Closed, key: dict[str, Any], tmp_path: Path
) -> None:
    """`dossier_sha256_rule` and `head_hash_rule`: the file is the template with the brief hash;
    the record holds the file's hash, the brief's hash and the head's own `result_sha256`, which is
    not the dossier's."""
    research = tmp_path / "research"
    shutil.copytree(closed.root / "research", research)  # never write into the shared tree
    record = rp.write_dossier(closed.execution(), research)
    dossier = key["cases"]["positive"]["dossier"]
    template = key["cases"]["positive"]["brief"]["template_file"]
    _, digest = brief_file(
        template, closed.head("CP-0").result_sha256, closed.head("CP-1").result_sha256
    )
    text = dossier["template_text"].replace(BRIEF_MARKER, digest)
    written = (research / "dossier.md").read_bytes()
    assert written == text.encode("utf-8")
    assert record.dossier_sha256 == sha(text) == sha(written)
    assert record.brief_sha256 == digest
    assert record.head_sha256 == closed.head("CP-DR").result_sha256
    assert record.head_sha256 != record.dossier_sha256


def test_run_json_takes_the_three_hashes_from_the_record(
    closed: Closed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`run.json`'s `cp_dr_*` keys are the record's (the staged run is S1's case; the record is the
    closed run's)."""
    monkeypatch.setattr(evidence, "research_clock", lambda: datetime(2026, 11, 2, tzinfo=UTC))
    case = ResearchCase(tmp_path)
    checked = check_arguments(**case.arguments(tmp_path))
    research = tmp_path / "copy" / "research"
    shutil.copytree(closed.root / "research", research)  # never write into the shared tree
    record = rp.write_dossier(closed.execution(), research)
    keys = rp._cp_dr_keys(checked, record)
    assert keys["cp_dr_dossier_sha256"] == sha((research / "dossier.md").read_bytes())
    assert keys["cp_dr_head_sha256"] == closed.head("CP-DR").result_sha256
    assert keys["cp_dr_brief_sha256"] == record.brief_sha256
    assert rp._cp_dr_keys(checked, None)["cp_dr_dossier_sha256"] is None


def test_the_delimiter_label_replaces_a_terminator_reason_in_the_dossier(
    closed: Closed, key: dict[str, Any], tmp_path: Path
) -> None:
    """A dossier over a fence-terminator refusal shows the key's label; `rejected.json` keeps the
    literal reason (`refusals/research/fence_terminator`)."""
    terminator = key["refusals"]["research"]["fence_terminator"]
    item = runs.oracle()["manifest"]["fence_terminator_item"]
    reason = f"evidence item {item['locator']} {terminator['reason_suffix']}"
    research = tmp_path / "research"
    shutil.copytree(closed.root / "research", research)
    refused = (
        *runs.refused_items(),
        RefusedItem(item["locator"], item["family"], None, reason),
    )
    write_rejected(research / evidence.REJECTED_FILE, refused)
    rp.write_dossier(closed.execution(), research)
    shown = (research / "dossier.md").read_text(encoding="utf-8")
    assert terminator["dossier_shown_reason"] in shown and reason not in shown
    assert reason in (research / evidence.REJECTED_FILE).read_text(encoding="utf-8")


def test_the_receipt_needs_the_evidence_record_and_names_it_when_it_is_gone(
    closed: Closed, tmp_path: Path
) -> None:
    """S1 review, item 14: the `ev-*` tool results take their retrieval times from
    `research/evidence.json`, which is outside the sealed store. Verification reads it; without it
    the verifier refuses with the named `identity_mismatch`, never skipping the `ev-*` calls."""
    moved = tmp_path / "run"
    shutil.copytree(closed.root, moved)
    shutil.rmtree(moved / "research")
    receipt = OwnerRunReceipt.model_validate_json((moved / "owner-run.json").read_bytes())
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        verify_owner_run_receipt(Execution(moved / "execution"), receipt)


# --- anchors at begin (O7-R20) -------------------------------------------------------------------


def test_a_blocked_cp0_head_is_not_anchored_and_nothing_is_written(
    tmp_path: Path, key: dict[str, Any]
) -> None:
    """`refusals/anchors/blocked_cp0`: a CP-0 head blocked by two invalid reviews stops the walk
    before CP-DR is begun, with the key's reason; no `brief.json`, no CP-DR attempt."""
    refusal = key["refusals"]["anchors"]["blocked_cp0"]
    workflow, pack = runs.start("positive", tmp_path)
    review = json.loads(runs.cp0_text(pack, "positive"))
    review["pack_sha256"] = "0" * 64  # a review that does not bind the pack is invalid, twice
    payload = json.dumps(review)
    runs.read_cited(workflow, payload)
    assert workflow.submit_review(payload)["status"] == "invalid"
    runs.read_cited(workflow, payload)
    with pytest.raises(CpDrNotAnchored) as raised:
        workflow.submit_review(payload)
    assert str(raised.value) == refusal["reason"]
    assert refusal["research_brief_json_written"] is False
    assert not (tmp_path / "research" / "brief.json").exists()
    assert all(a.module_id != "CP-DR" for a in Execution(tmp_path / "store").read().attempts)


# --- the entry the prompt rules start from -------------------------------------------------------


def test_each_steps_rule_entry_is_the_validator_the_entry_validator_dispatches_to() -> None:
    """`prompts/rules.py` starts a CP-DR step's rule coverage at that step's validator (one
    `ENTRY_VALIDATOR` serves both steps); this is the guard that the declared entries are what
    `ENTRY_VALIDATOR` calls."""
    tree = ast.parse((ROOT / "src/deploy_workflow/owners/cpdr.py").read_text(encoding="utf-8"))
    entry = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "ENTRY_VALIDATOR"
    )
    called = {n.id for n in ast.walk(entry) if isinstance(n, ast.Name)}
    for step, name in (("brief", "_validate_brief"), ("research", "_validate_research")):
        assert rules.ENTRIES[step] == (rules.OWNERS + f"cpdr:{name}",)
        assert name in called
    assert cpdr.STEP_IDS == ("brief", "research")


# --- the fault form on the run path (O7-R32) -----------------------------------------------------


def test_a_stop_caused_by_a_brief_fault_keeps_the_faults_own_form() -> None:
    stop = StepStopped("WorkflowError", "BriefInvalid: x", cause=BriefInvalid("x"))
    assert rp._fault_reason(stop, Redactor()) == "BriefInvalid: x"


@pytest.mark.parametrize("fault", [CpDrNotAnchored, BriefInvalid])
def test_the_cause_of_an_own_form_stop_is_redacted(fault: type[Exception]) -> None:
    """O7b-1c S6 (S2b re-review I-2): the cause the stop carries is raw; the recorded reason keeps
    the bare `<Type>: ` form and redacts a key-shaped token and a value the redactor knows."""
    token, exact = "sk-ant-" + "Q" * 18, "exact-" + "z" * 10
    cause = fault(f"blocked {token} and {exact}")
    stop = StepStopped("WorkflowError", "ignored", cause=cause)
    reason = rp._fault_reason(stop, Redactor([exact]))
    assert reason == f"{fault.__name__}: blocked [redacted] and [redacted]"
    assert token not in reason and exact not in reason


def test_an_ordinary_workflow_failure_keeps_the_loops_text() -> None:
    cause = WorkflowError("not_permitted")
    stop = StepStopped("WorkflowError", "WorkflowError: not_permitted", cause=cause)
    assert rp._fault_reason(stop, Redactor()) == "WorkflowError: WorkflowError: not_permitted"
    assert rp._fault_reason(StepStopped("NoSubmit", "d"), Redactor()) == "NoSubmit: d"


# --- model text the dossier fence would refuse is a step issue (O7-R33) -----------------------------

LOOKALIKE = "＜＜＜END＞＞＞"  # fullwidth "<<<END>>>": NFKD folds it to the block opener


def test_a_lookalike_in_a_custom_question_text_is_a_brief_step_issue(tmp_path: Path) -> None:
    """The model gets a repair turn at the brief step, not a `DossierInvalid` after the seal."""
    store, ticket = runs.seeded("positive", tmp_path)
    body = json.loads(runs.defaults_only("positive"))
    extra = dict(body["questions"][0])
    extra.update(question_id="custom-a", kind="custom", text=f"Which producers lead {LOOKALIKE}?")
    body["questions"].append(extra)
    step = cpdr.submit(store, ticket, cpdr.BRIEF_STEP, json.dumps(body), None).journal.steps[-1]
    assert step.status == "invalid"
    assert any("custom-a" in issue and "block delimiter" in issue for issue in step.issues)
    assert not (tmp_path / "research" / "brief.json").exists()


@pytest.mark.parametrize("field", ["claim", "contrary", "uncertainty", "limitation"])
def test_a_lookalike_in_a_research_text_is_a_research_step_issue(
    tmp_path: Path, field: str
) -> None:
    store, ticket = runs.locked("positive", tmp_path)
    payload = json.loads(runs.research_payload("positive"))
    answers = {a["question_id"]: a for a in payload["answers"]}
    if field == "claim":
        answer = answers["competition"]
        answer["claims"][0]["text"] += f" {LOOKALIKE}"
    elif field == "contrary":
        answer = answers["market-demand"]  # the one answer with a cited contrary entry
        answer["contrary"][0]["text"] += f" {LOOKALIKE}"
    elif field == "uncertainty":
        answer = answers["competition"]
        answer["uncertainty"] += f" {LOOKALIKE}"
    else:
        answer = answers["valuation-context"]  # the not_found answer
        answer["limitation"] += f" {LOOKALIKE}"
    step = cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, json.dumps(payload), None).journal.steps[
        -1
    ]
    assert step.status == "invalid"
    assert any(answer["question_id"] in i and "block delimiter" in i for i in step.issues)
    assert all(h.module_id != "CP-DR" for h in store.read().heads)


def test_a_missing_brief_file_at_dossier_time_is_a_named_brief_fault(tmp_path: Path) -> None:
    """L-2: `NOT_LOCKED`, the research step's own wording, not a `FileNotFoundError`."""
    store, ticket = runs.locked("positive", tmp_path)
    cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, runs.research_payload("positive"), None)
    head = next(h for h in store.read().heads if h.module_id == "CP-DR")
    (tmp_path / "research" / "brief.json").unlink()
    with pytest.raises(BriefInvalid, match=cpdr.NOT_LOCKED):
        cpdr.dossier_input(store, head, tmp_path / "research")


# --- anchors through the walk's begin hook (O7-R20; plan 4 row 6) ----------------------------------


def blocked_cp1(store: Execution) -> None:
    runs.edit_head(store, "CP-1", status="blocked")


def stale_cp0(store: Execution) -> None:
    runs.edit_head(store, "CP-0", status="stale", notes=("Input changed; rerun required",))


def other_cp0_input(store: Execution) -> None:
    """CP-1 re-settled over a CP-0 input with one hex digit altered: a consistent blob and head."""
    head = next(h for h in store.read().heads if h.module_id == "CP-1")
    module = store.result(head.result_sha256)
    inputs = tuple(
        i.model_copy(update={"sha256": ("0" if i.sha256[0] != "0" else "1") + i.sha256[1:]})
        if i.input_id == "CP-0"
        else i
        for i in module.inputs
    )
    runs.edit_head(store, "CP-1", forged=module.model_copy(update={"inputs": inputs}))


@pytest.mark.parametrize(
    ("name", "edit"),
    [("blocked_cp1", blocked_cp1), ("stale_head", stale_cp0), ("input_cp0_hash", other_cp0_input)],
)
def test_anchor_refusals(tmp_path: Path, key: dict[str, Any], name: str, edit: Any) -> None:
    """`refusals/anchors/<name>`: the begin hook raises `CpDrNotAnchored` with the key's reason;
    nothing is written (no `brief.json`) and no CP-DR attempt is begun."""
    want = key["refusals"]["anchors"][name]
    store = runs.settled_pair("positive", tmp_path)
    edit(store)
    with pytest.raises(CpDrNotAnchored) as raised:
        owner_workflow._PRE_BEGIN["CP-DR"](store, store.read())
    assert str(raised.value) == want["reason"]
    assert not (tmp_path / "research" / "brief.json").exists()
    assert all(a.module_id != "CP-DR" for a in store.read().attempts)


class _RecordingStore:
    """The store `_begin` reads, recording every `begin` it is asked for."""

    def __init__(self, inner: Execution) -> None:
        self._inner = inner
        self.begun: list[str] = []

    def read(self) -> Any:
        return self._inner.read()

    def result(self, digest: str) -> Any:
        return self._inner.result(digest)

    def begin(self, module_id: str) -> Any:
        self.begun.append(module_id)
        return self._inner.begin(module_id)


def test_anchors_with_cp1_unrun_name_cp1_not_the_edge_through_begin(tmp_path: Path) -> None:
    """O7-R42 M-1: with CP-1 never run, `OwnerWorkflow._begin("CP-DR")` raises `CpDrNotAnchored`
    naming CP-1 before `store.begin` is asked (the hook runs before `current_inputs`), not the
    edge's 'Required upstream is unrun, stale or blocked'."""
    store = _RecordingStore(runs.settled_pair("positive", tmp_path, ("CP-0",)))
    stand_in: Any = SimpleNamespace(_store=store, _refusals=[], _refusal_kind=None)
    with pytest.raises(CpDrNotAnchored) as raised:
        owner_workflow.OwnerWorkflow._begin(stand_in, "CP-DR")
    message = str(raised.value)
    assert "CP-1" in message
    assert "BLOCKED_EDGE" not in message and "unrun, stale or blocked" not in message
    assert store.begun == []


def test_the_begin_hook_calls_check_anchors_with_the_snapshots_heads_and_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = runs.settled_pair("positive", tmp_path)
    snapshot = store.read()
    seen: list[tuple[Any, ...]] = []

    def spy(cp0: Any, cp1: Any, run: Any) -> Any:
        seen.append((cp0, cp1, run))
        return check_anchors(cp0, cp1, run)

    monkeypatch.setattr(cpdr, "check_anchors", spy)
    owner_workflow._PRE_BEGIN["CP-DR"](store, snapshot)
    [(cp0, cp1, run)] = seen
    heads = {h.module_id: h for h in snapshot.heads}
    assert (cp0.head, cp1.head) == (heads["CP-0"], heads["CP-1"])
    assert cp0.module == store.result(heads["CP-0"].result_sha256)
    assert cp1.module == store.result(heads["CP-1"].result_sha256)
    assert run == snapshot.run


# --- the brief lock (plan 4 row 7) ------------------------------------------------------------------


def locked_brief(store: Execution) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (cpdr.research_dir(store) / cpdr.BRIEF_FILE).read_text(encoding="utf-8")
    )
    return loaded


def test_brief_locks_forty_to_thirty_two(tmp_path: Path, key: dict[str, Any]) -> None:
    """`brief/lock`: 40 tailored questions lock as 32, the context questions first, the tail
    dropped, through `submit("brief")`."""
    want = key["brief"]["lock"]
    tailored = json.loads(runs.brief_payload("positive"))["questions"]
    assert want["tailored_in"] == len(tailored) + len(want["context_kept"])  # plus the context's
    store, ticket = runs.seeded("positive", tmp_path)
    step = cpdr.submit(store, ticket, cpdr.BRIEF_STEP, runs.brief_payload("positive"), None)
    assert step.journal.steps[-1].status == "valid"
    ids = [q["question_id"] for q in locked_brief(store)["questions"]]
    assert ids == want["locked_ids"] and len(ids) == want["locked_out"]
    assert ids[: len(want["context_kept"])] == want["context_kept"]
    assert not set(want["dropped_from_tail"]) & set(ids)


def test_missing_default_is_an_invalid_step(tmp_path: Path) -> None:
    """A brief without one of the six defaults is a journaled invalid step naming it; nothing is
    locked."""
    store, ticket = runs.seeded("positive", tmp_path)
    questions = [
        q
        for q in runs.oracle()["submissions"]["brief"]["model_tailored_defaults_only"]
        if q["question_id"] != "competition"
    ]
    step = cpdr.submit(
        store, ticket, cpdr.BRIEF_STEP, runs.brief_payload("positive", questions), None
    ).journal.steps[-1]
    assert step.status == "invalid"
    assert any("competition" in issue and "missing" in issue for issue in step.issues)
    assert not (cpdr.research_dir(store) / cpdr.BRIEF_FILE).exists()


def test_lock_exists_before_research_begins(tmp_path: Path) -> None:
    store, ticket = runs.seeded("positive", tmp_path)
    path = cpdr.research_dir(store) / cpdr.BRIEF_FILE
    assert not path.exists()
    journal = cpdr.submit(store, ticket, cpdr.BRIEF_STEP, runs.defaults_only("positive"), None)
    assert [s.step_id for s in journal.journal.steps] == [cpdr.BRIEF_STEP]
    assert path.exists()


def test_deleted_brief_is_the_named_refusal(tmp_path: Path) -> None:
    """Research after the lock file is gone is `BriefInvalid(NOT_LOCKED)`; no research step is
    journaled."""
    store, ticket = runs.locked("positive", tmp_path)
    (cpdr.research_dir(store) / cpdr.BRIEF_FILE).unlink()
    with pytest.raises(BriefInvalid, match=cpdr.NOT_LOCKED):
        cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, runs.research_payload("positive"), None)
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    assert [s.step_id for s in attempt.steps] == [cpdr.BRIEF_STEP]


def test_edit_after_lock_is_hash_mismatch(tmp_path: Path, key: dict[str, Any]) -> None:
    """`refusals/research/edit_after_lock`: a hashed field of `brief.json` changed after the lock,
    then research submitted, is `BriefInvalid` with the key's message; the step is not journaled."""
    want = key["refusals"]["research"]["edit_after_lock"]
    store, ticket = runs.locked("positive", tmp_path)
    path = cpdr.research_dir(store) / cpdr.BRIEF_FILE
    body = json.loads(path.read_text(encoding="utf-8"))
    body["questions"][0]["text"] = key["brief"]["edit_after_lock"]["edit_vector"][
        "edited_question_text"
    ]
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(BriefInvalid) as raised:
        cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, runs.research_payload("positive"), None)
    assert type(raised.value).__name__ == want["exception"]
    assert str(raised.value) == want["message"]
    attempt = next(a for a in store.read().attempts if a.ticket_id == ticket)
    assert [s.step_id for s in attempt.steps] == [cpdr.BRIEF_STEP]


# --- the research step (plan 4 rows 10, 11) ---------------------------------------------------------


def test_research_v1_states_counts_readiness(tmp_path: Path, key: dict[str, Any]) -> None:
    """`cases/positive/{claim_state_list,counts,readiness}` from the settled head; the
    `valuation-context` not_found answer gives `missing` TDR.3 facts with the limitation and no
    amount; `ev-3` supports the competition claim and is market-demand's cited contrary."""
    want = key["cases"]["positive"]
    store, ticket = runs.locked("positive", tmp_path)
    cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, runs.research_payload("positive"), None)
    head = next(h for h in store.read().heads if h.module_id == "CP-DR")
    given = cpdr.dossier_input(store, head, cpdr.research_dir(store))
    assert list(given.claim_states) == want["claim_state_list"]
    assert render_dossier(given).readiness == want["readiness"]
    facts = {f.fact_id: f for f in store.head_module(head).facts}
    for name, value in want["counts"].items():
        assert str(facts[f"TDR.3.total.{name}"].amount) == value
    limitation = next(
        f["limitation"] for f in want["facts"] if f["fact_id"] == "TDR.3.valuation-context.answer"
    )
    for field in ("answer", "contrary", "uncertainty"):
        fact = facts[f"TDR.3.valuation-context.{field}"]
        assert (fact.status, fact.amount, fact.limitation) == ("missing", None, limitation)
    contrary = facts["TDR.3.market-demand.contrary"]  # the settled head's own facts
    assert "ev-3" in [c.source_id for c in contrary.citations]
    evidence_id = facts["TDR.2.competition.c1.evidence_id"].text or ""
    assert "ev-3" in evidence_id.split("; ")


def research_with(text_for: str, text: str) -> str:
    """`research_v1` with `text` as the `uncertainty` of the question `text_for`."""
    body = json.loads(runs.research_payload("positive"))
    next(a for a in body["answers"] if a["question_id"] == text_for)["uncertainty"] = text
    return json.dumps(body)


def test_research_refusals_families_not_independent(tmp_path: Path, key: dict[str, Any]) -> None:
    want = key["refusals"]["research"]["families_not_independent"]
    submission = runs.oracle()["submissions"]["refusal_inputs"]["independence"]
    store, ticket = runs.locked("positive", tmp_path)
    step = cpdr.submit(store, ticket, cpdr.RESEARCH_STEP, json.dumps(submission), None)
    journal = step.journal.steps[-1]
    assert journal.status == "invalid"
    assert any(issue.endswith(want["text"]) for issue in journal.issues)


def test_research_refusals_banned_word(tmp_path: Path, key: dict[str, Any]) -> None:
    """`recommend` is refused with the key's text; `covenant`, `recovery` and `refinancing` are
    accepted in the same place."""
    want = key["refusals"]["research"]["banned_word"]
    question = runs.oracle()["submissions"]["refusal_inputs"]["banned_word"]["question_id"]
    store, ticket = runs.locked("positive", tmp_path / "refused")
    refused = cpdr.submit(
        store, ticket, cpdr.RESEARCH_STEP, research_with(question, want["refused"]), None
    ).journal.steps[-1]
    assert refused.status == "invalid"
    assert any(issue.endswith(want["refused_text"]) for issue in refused.issues)
    store, ticket = runs.locked("positive", tmp_path / "accepted")
    accepted = cpdr.submit(
        store, ticket, cpdr.RESEARCH_STEP, research_with(question, want["accepted"]), None
    ).journal.steps[-1]
    assert (accepted.status, accepted.issues) == ("valid", ())


# --- the fence (plan 4 row 12) ----------------------------------------------------------------------


def test_fence_in_prompt_and_tool_result(closed: Closed, key: dict[str, Any]) -> None:
    """`fence/{injection_phrase,prompt,read_pages,connector_calls}`: the phrase is in `ev-3`'s
    text; it appears in the composed research prompt and in the `read_pages` result only inside
    `ev-3`'s UNTRUSTED_EVIDENCE block, and no socket was opened."""
    fence = key["fence"]
    block = re.compile(rf"<<<UNTRUSTED_EVIDENCE id={fence['item']} .*?<<<END>>>", re.DOTALL)
    for shown in (closed.run.prompt, closed.run.read_body):
        inside = block.findall(shown)
        assert inside and all(fence["injection_phrase"] in text for text in inside)
        assert fence["injection_phrase"] not in block.sub("", shown)
    assert closed.run.sockets == fence["connector_calls"]


# --- ceiling and lineage (plan 4 row 14) ------------------------------------------------------------


def test_ceiling_and_lineage(closed: Closed, key: dict[str, Any]) -> None:
    """The readiness is never `COMMITTEE_READY`; the lineage is in the dossier and in `run.json`."""
    dossier = (closed.root / "research" / "dossier.md").read_text(encoding="utf-8")
    readiness = re.search(r"^readiness: (\S+)$", dossier, re.MULTILINE)
    assert readiness is not None
    assert readiness.group(1) == key["cases"]["positive"]["readiness"] != "COMMITTEE_READY"
    assert f"cp_dr_lineage: {key['cp_dr_lineage']}" in dossier
    written = json.loads((closed.root / "run.json").read_text(encoding="utf-8"))
    assert written["cp_dr_lineage"] == key["cp_dr_lineage"]


# --- the second run (plan 4 row 15) -----------------------------------------------------------------


def test_closed_run_v2(closed: Closed, key: dict[str, Any], tmp_path: Path) -> None:
    """`cases/v2`: a fresh run id and `research_v2`; the facts and the dossier are v2's; the brief
    questions are v1's and `brief_sha256` differs (it hashes the run id and the anchors)."""
    want = key["cases"]["v2"]
    store_path, receipt_path, _ = runs.cpdr_closed("v2", tmp_path)
    store = Execution(store_path)
    verify_owner_run_receipt(store, OwnerRunReceipt.model_validate_json(receipt_path.read_bytes()))
    head = next(h for h in store.read().heads if h.module_id == "CP-DR")
    assert head.status == want["cp_dr_head_status_expected"]
    assert store.read().run.run_id == want["run_id"]
    module = store.head_module(head)
    by_id = {fact.fact_id: fact for fact in module.facts}
    assert sorted(by_id) == sorted(f["fact_id"] for f in want["facts"])
    for wanted in want["facts"]:
        fact = by_id[wanted["fact_id"]]
        got = {n: None if (v := getattr(fact, n)) is None else str(v) for n in FACT_FIELDS}
        assert got == {n: wanted.get(n) for n in FACT_FIELDS}, fact.fact_id
    research = tmp_path / "research"
    rp.write_dossier(store, research)
    template = want["brief"]["template_file"]
    _, digest = brief_file(
        template, closed_head(store, "CP-0").result_sha256, closed_head(store, "CP-1").result_sha256
    )
    text = want["dossier"]["template_text"].replace(BRIEF_MARKER, digest)
    assert (research / "dossier.md").read_bytes() == text.encode("utf-8")
    first = json.loads((closed.root / "research" / "brief.json").read_text(encoding="utf-8"))
    second = json.loads((research / "brief.json").read_text(encoding="utf-8"))
    assert second["questions"] == first["questions"]
    assert second["brief_sha256"] != first["brief_sha256"]
    for field in ("as_of", "cutoff", "version", "peer_pack"):
        assert second[field] == first[field], field


def closed_head(store: Execution, module_id: str) -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


# --- a forged fact (plan 4 row 16) ------------------------------------------------------------------


def test_forged_fact_is_refused_by_the_probe(closed: Closed, tmp_path: Path) -> None:
    """A TDR fact changed in the store, with a consistent blob and head, is refused at `probe`
    (`identity_mismatch`), and the sealed receipt no longer verifies."""
    moved = tmp_path / "run"
    shutil.copytree(closed.root, moved)
    store = Execution(moved / "execution")
    head = closed_head(store, "CP-DR")
    module = store.head_module(head)
    facts = tuple(
        f.model_copy(update={"amount": (f.amount or Decimal(0)) + 1}) if f.fact_id == FORGED else f
        for f in module.facts
    )
    forged = module.model_copy(update={"facts": facts})
    runs.edit_head(store, "CP-DR", forged=forged)
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cpdr.probe(store, snapshot, attempt)  # the honest attempt, over the forged head
    receipt = OwnerRunReceipt.model_validate_json((moved / "owner-run.json").read_bytes())
    with pytest.raises(
        WorkflowError, match="stale_binding"
    ):  # the sealed head hash no longer binds
        verify_owner_run_receipt(Execution(moved / "execution"), receipt)
