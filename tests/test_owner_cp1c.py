"""CP-1C store runs (Stage 5 only): genuine CP-0 and CP-1 promotions, then CP-1C, through the
public `OwnerWorkflow` API, compared with `cases/cp1c-owner/expected.json`. Each promotion is
11-26 minutes (three, module-scoped: positive, gap, no_peers; the closed runs and every A3 fork
are clones of those waiting states; one job under the heavy-job lock). Written in Stage 2, never
run there. Covers the lease Acceptance section item by item:
- A1 positive, A1b gap, A1c no_peers: plan, statuses, the CP-1C head against the oracle (facts,
  tables, claims, own and inherited limitations, FP03 cells), `prose_issues`, the tail input,
  the tool use (one ok `read_inputs`, ok `read_pages` over every cited page, the `no_peers`
  search) and the CP-1 readiness assessment (ruling S6);
- A2 refused (CP-0 only, the CP-1 begin refused);
- A3 refusals r01-r10 and r12-r14 on clones (r11 needs the `peer_table_not_found` fixture pack,
  which the oracle uses with no run; its validator form is fast), blocked (r04 twice), t01-t03,
  stale_binding per upstream and model text at run level;
- A4 tamper (`expected.json#tamper`, the CP-DR rev 4 recipe) and the step-output blob check;
- A5 fixtures are Stage 1 (`tests/test_method_cp1c.py`); A6 `test_owner_workflow.py` and
  `test_owner_s1a.py` run as their own files;
- A7 D8 and the bindings on the settled heads (the G2 page is Stage 3); D3 stays open: the
  reader over the genuine heads, no consumer.
The fast forms over hand-seeded heads are `tests/test_connect_cp1c.py`.
"""

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

import cp1c_runs as runs
import pytest
import test_method_cp1c as stage1
import view_tree
from defect_classes import model_text_failures
from s1a_runs import clone_workflow
from test_connect_cp1c import CP1C_VERBATIM, assert_equals_oracle, assert_fp03_cells

from deploy_vii import registry
from deploy_vii.bindings import validate_bindings
from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import Fact, Module, ModuleView, View, validate_tables
from deploy_vii.downstream_readiness import DownstreamReport, validate_downstream_review
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, head_of
from deploy_vii.live.tools import cited_locators
from deploy_vii.prose import prose_issues
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.owners import cp1c
from deploy_workflow.workflow import WorkflowError

EXPECTED: dict[str, Any] = runs.oracle()["expected"]
SUBMISSIONS: dict[str, Any] = runs.oracle()["submissions"]
MODULE = "CP-1C"
SYNTHETIC = "Synthetic case; not real issuer qualification"
Closed = tuple[Path, Path, None]
REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
EXPECTED_REFUSALS = {r["id"]: r for r in EXPECTED["refusals"]}
RUN_LEVEL = [rid for rid, r in REFUSALS.items() if r["pack"] != "unparseable"]
TOOLS = {t["id"]: t for t in EXPECTED["tool_refusals"]}
VIEW_KEYS = ["upstream", "peers", "cp1_facts", "rules", "inherited_limitations"]  # lease D2


def _ready(case: str, factory: pytest.TempPathFactory) -> OwnerWorkflow:
    return runs.promoted(case, factory.mktemp(f"cp1c-{case}-ready"))[0]


@pytest.fixture(scope="module")
def ready_positive(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    return _ready("positive", tmp_path_factory)


@pytest.fixture(scope="module")
def ready_gap(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    return _ready("gap", tmp_path_factory)


@pytest.fixture(scope="module")
def ready_no_peers(tmp_path_factory: pytest.TempPathFactory) -> OwnerWorkflow:
    return _ready("no_peers", tmp_path_factory)


def _closed(template: OwnerWorkflow, case: str, root: Path) -> Closed:
    runs.close(clone_workflow(template, root), case, root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json", None


@pytest.fixture(scope="module")
def positive(ready_positive: OwnerWorkflow, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return _closed(ready_positive, "positive", tmp_path_factory.mktemp("cp1c-positive"))


@pytest.fixture(scope="module")
def gap(ready_gap: OwnerWorkflow, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return _closed(ready_gap, "gap", tmp_path_factory.mktemp("cp1c-gap"))


@pytest.fixture(scope="module")
def no_peers(ready_no_peers: OwnerWorkflow, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return _closed(ready_no_peers, "no_peers", tmp_path_factory.mktemp("cp1c-no-peers"))


@pytest.fixture(scope="module")
def blocked(ready_positive: OwnerWorkflow, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return _closed(ready_positive, "blocked", tmp_path_factory.mktemp("cp1c-blocked"))


@pytest.fixture(scope="module")
def refused(tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return runs.cp1c_closed("refused", tmp_path_factory.mktemp("cp1c-refused"))


def _receipt(closed: Closed) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json(closed[1].read_bytes())


def _verify(closed: Closed) -> Execution:
    store = Execution(closed[0])
    ow.verify_owner_run_receipt(store, _receipt(closed))
    return store


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _attempts(store: Execution) -> list[Attempt]:
    return [a for a in store.read().attempts if a.module_id == MODULE]


def _selected(store: Execution) -> dict[str, Fact]:
    """The CP-1 T4.10 fact of each metric by `manifest.json cp1_fact_selection_rule` (label and
    period as Stage 1 reads them from the rule; exactly one each)."""
    facts = store.head_module(_head(store, "CP-1")).facts
    out: dict[str, Fact] = {}
    for key, rule in stage1.cp1_metrics().items():
        hits = [
            f
            for f in facts
            if (f.table_id, f.period, f.label) == ("T4.10", rule.period, rule.label)
        ]
        assert len(hits) == 1, key
        out[key] = hits[0]
    return out


def _tree(path: Path) -> dict[str, str]:
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


# --- A1 positive, A1b gap, A1c no_peers ----------------------------------------------------------


@pytest.mark.parametrize("case", stage1.CASES)
def test_a1_plan_statuses_and_the_cp1c_head_equal_the_oracle(
    case: str, request: pytest.FixtureRequest
) -> None:
    closed: Closed = request.getfixturevalue(case)
    store = _verify(closed)
    plan = EXPECTED["execution"]["plan_order"]
    assert _receipt(closed).plan == tuple(plan)
    assert [h.module_id for h in store.read().heads] == plan
    assert {h.status for h in store.read().heads} == {"restricted"}
    module = store.head_module(_head(store, MODULE))
    want = EXPECTED["cases"][case]
    assert module.status == want["module_status"]
    assert_equals_oracle(case, module.facts, module.tables, module.claims, _selected(store))
    assert list(module.limitations) == want["settled_limitations"]
    assert module.limitations[-1] == SYNTHETIC
    assert prose_issues(module, names=(store.pack().run.issuer_name,)) == ()
    assert_fp03_cells(case, module)


@pytest.mark.parametrize("case", stage1.CASES)
def test_a1_inherited_limitations_follow_the_bound_heads(
    case: str, request: pytest.FixtureRequest
) -> None:
    """execution.py:345-366 over the genuine CP-0 and CP-1 heads: their own and inherited lines,
    de-duplicated, never repeating CP-1C's own."""
    store = _verify(request.getfixturevalue(case))
    module = store.head_module(_head(store, MODULE))
    texts: list[str] = []
    for upstream in ("CP-0", "CP-1"):
        bound = store.head_module(_head(store, upstream))
        texts.extend((*bound.limitations, *bound.inherited_limitations))
    want = tuple(t for t in dict.fromkeys(texts) if t not in module.limitations)
    assert module.inherited_limitations == want


@pytest.mark.parametrize("case", stage1.CASES)
def test_a1_the_settled_head_binds_its_upstream_and_its_tail_input(
    case: str, request: pytest.FixtureRequest
) -> None:
    store = _verify(request.getfixturevalue(case))
    (attempt,) = _attempts(store)
    heads = {h.module_id: h for h in store.read().heads}
    assert [item.input_id for item in attempt.inputs] == ["prepared-pack", "CP-0", "CP-1"]
    bound = {item.input_id: item for item in attempt.inputs}  # the pack input has no head
    assert bound["prepared-pack"].sha256 == store.read().pack_sha256
    for upstream in ("CP-0", "CP-1"):
        assert (bound[upstream].sha256, bound[upstream].status) == (
            heads[upstream].result_sha256,
            heads[upstream].status,
        )
    module = store.head_module(heads[MODULE])
    text = json.dumps(SUBMISSIONS[case][runs.STEP], ensure_ascii=False)
    submission = cp1c.PeerBenchmarkSubmission.model_validate_json(text)
    assert (module.inputs[-1].input_id, module.inputs[-1].sha256) == (
        cp1c.SUBMISSION_INPUT,
        submission.content_hash(),
    )
    assert attempt.result_sha256 == heads[MODULE].result_sha256


@pytest.mark.parametrize("case", stage1.CASES)
def test_a1_tool_use_is_one_read_and_the_cited_pages(
    case: str, request: pytest.FixtureRequest
) -> None:
    """Exactly one ok `read_inputs` (the exact view, no quote of any head); ok `read_pages` over
    every cited page:N; `no_peers`: one ok unscoped `search_pack` returning no span."""
    closed: Closed = request.getfixturevalue(case)
    receipt = _receipt(closed)
    reads = [r for r in receipt.input_reads if r.binding.module_id == MODULE]
    calls = [c for c in receipt.calls if c.binding.module_id == MODULE and c.status == "ok"]
    assert len(reads) == 1
    assert reads[0].inputs_sha256 == hashlib.sha256(reads[0].body.encode()).hexdigest()
    assert list(json.loads(reads[0].body)) == VIEW_KEYS
    view_tree.check("cp1c", case, reads[0].body)
    store = _verify(closed)
    quotes = {
        c.quote for h in store.read().heads for f in store.head_module(h).facts for c in f.citations
    }
    assert not [q for q in quotes if q in reads[0].body]
    covered = {
        (c.arguments["source_id"], f"page:{n}")
        for c in calls
        if c.tool == "read_pages"
        for n in range(c.arguments["first_page"], c.arguments["last_page"] + 1)
    }
    payload = json.dumps(SUBMISSIONS[case][runs.STEP], ensure_ascii=False)
    assert set(cited_locators(payload)) <= covered
    searches = [c for c in calls if c.tool == "search_pack"]
    if case == "no_peers":
        (search,) = searches
        expect = SUBMISSIONS["no_peers"]["tool_calls"][1]
        assert search.arguments == expect["arguments"]
        assert (search.body or "").splitlines()[0] == expect["expect_header"]
    else:
        assert searches == []


@pytest.mark.parametrize("case", stage1.CASES)
def test_a1_cp1_readiness_assesses_cp1c_as_the_oracle(
    case: str, request: pytest.FixtureRequest
) -> None:
    """Ruling S6 on the genuine CP-1 head: the bound literal validates and CP-1C's row is the
    expected assessment. A mismatch goes to LEAD; the oracle is not edited."""
    store = _verify(request.getfixturevalue(case))
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    step = next(s for s in attempt.steps if s.step_id == "readiness")
    report = DownstreamReport.model_validate_json(store.step_output(step.output_sha256 or ""))
    assert validate_downstream_review(report.inputs, report.review) == ()
    want = SUBMISSIONS[case]["cp1_readiness"]["expected_assessment"][MODULE]
    row = next(r for r in report.consumers if r.canonical_module == MODULE)
    assert row.status == want["status"]


def test_a1_cp0_commands_run_cp1_and_cp1c(positive: Closed) -> None:
    store = _verify(positive)
    commands = [[c.row_id, c.text] for c in _head(store, "CP-0").commands]
    assert commands == EXPECTED["execution"]["cp0_t8"]["positive"]


def test_a1_verification_writes_nothing(positive: Closed) -> None:
    before = _tree(positive[0])
    store = _verify(positive)
    cp1c.cp1c_reader(store, _head(store, MODULE))
    assert _tree(positive[0]) == before


# --- A2 refused ------------------------------------------------------------------------------------


def test_a2_refused_begin_for_cp1_and_no_cp1c_anywhere(refused: Closed) -> None:
    store = _verify(refused)
    want = EXPECTED["cases"]["refused"]
    reason = want["refused_begins"][0]["reason"].removeprefix("str(NotAuthorized): ")
    assert [(r.module_id, r.reason) for r in _receipt(refused).refusals] == [("CP-1", reason)]
    assert [a.module_id for a in store.read().attempts] == want["attempts"]
    assert [h.module_id for h in store.read().heads] == want["heads"]
    commands = {c.row_id: c.text for c in _head(store, "CP-0").commands}
    assert commands == want["CP-0"]["T8_commands"]
    assert _receipt(refused).model is None


# --- A3 refusals, blocked, tool use (forks of the waiting states) ---------------------------------


@pytest.mark.parametrize("rid", RUN_LEVEL)
def test_a3_each_refusal_is_journaled_with_the_oracle_issues(
    rid: str, request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    template = request.getfixturevalue(f"ready_{REFUSALS[rid]['base_case']}")
    workflow = clone_workflow(template, tmp_path)
    outcome = runs.drive_refusal(workflow, rid)
    assert outcome["status"] == "invalid"
    want = EXPECTED_REFUSALS[rid]["expected_issues"]
    assert len(outcome["issues"]) == len(want), outcome["issues"]
    assert all(stage1._matches(i, w) for i, w in zip(outcome["issues"], want, strict=True))
    assert not [h for h in workflow._store.read().heads if h.module_id == MODULE]


def test_a3_blocked_settles_a_blocked_head_with_the_issue_in_its_limitations(
    blocked: Closed,
) -> None:
    store = _verify(blocked)
    want = EXPECTED["blocked"]
    head = _head(store, MODULE)
    module = store.head_module(head)
    assert head.status == want["head_status"]
    assert module.tables == () and module.facts == ()
    assert want["limitations_contain"] in module.limitations
    attempts = _attempts(store)
    assert [a.number for a in attempts] == [0, 1]
    assert attempts[1].repair_of == attempts[0].ticket_id
    assert cp1c.cp1c_reader(store, head) == cp1c.Cp1cHead(
        status="blocked", head_sha256=head.result_sha256
    )


def test_a3_t01_unread_page_is_invalid_then_repaired_to_a_verifying_receipt(
    ready_positive: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(ready_positive, tmp_path)
    t01 = TOOLS["t01"]
    first = runs.drive_cp1c(workflow, "positive", calls=t01["calls_before_submit"])
    assert (first["status"], first["issues"]) == ("invalid", t01["expected_issues"])
    second = runs.drive_cp1c(workflow, "positive")
    assert second["status"] == "valid"
    workflow.write_receipt(tmp_path / "owner-receipt.json")
    store = _verify((tmp_path / "store", tmp_path / "owner-receipt.json", None))
    attempts = _attempts(store)
    assert [a.number for a in attempts] == [0, 1]
    assert attempts[1].repair_of == attempts[0].ticket_id


def test_a3_t02_a_non_pack_tool_is_refused_and_journals_nothing(
    ready_positive: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(ready_positive, tmp_path)
    call = TOOLS["t02"]["call"]
    outcome = workflow.invoke(call["tool"], call["arguments"])
    want = TOOLS["t02"]["expected_receipt"]
    assert (outcome["status"], outcome["error_code"]) == (want["status"], want["reason"])
    assert [(a.number, a.status, a.steps) for a in _attempts(workflow._store)] == [
        (0, "pending", ())
    ]


def test_a3_t03_submit_before_read_inputs_is_not_permitted(
    ready_positive: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(ready_positive, tmp_path)
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(json.dumps(SUBMISSIONS["positive"][runs.STEP]))
    assert caught.value.code == TOOLS["t03"]["expected_receipt"]["reason"]
    assert [(a.number, a.status, a.steps) for a in _attempts(workflow._store)] == [
        (0, "pending", ())
    ]


@pytest.mark.parametrize("upstream_id", ["CP-0", "CP-1"])
def test_a3_a_new_upstream_head_between_read_and_submit_is_stale_binding(
    upstream_id: str, ready_positive: OwnerWorkflow, tmp_path: Path
) -> None:
    workflow = clone_workflow(ready_positive, tmp_path)
    runs.run_calls(workflow, SUBMISSIONS["positive"]["tool_calls"])
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
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(json.dumps(SUBMISSIONS["positive"][runs.STEP]))
    assert caught.value.code == "stale_binding"
    assert [(a.number, a.status, a.steps) for a in _attempts(store)] == [(0, "pending", ())]


class _Fresh:
    """One fresh fork of the positive waiting state per hostile value (`model_text_failures`):
    the literal tool sequence, then the text."""

    waiting: OwnerWorkflow
    root: Path
    made = 0

    def __init__(self) -> None:
        _Fresh.made += 1
        self.workflow = clone_workflow(self.waiting, self.root / f"run{_Fresh.made}")

    def submit_review(self, text: str) -> dict[str, Any]:
        return runs.drive_cp1c(self.workflow, "positive", text=text)


def test_a3_model_text_is_refused_or_verbatim_and_never_wedges(
    ready_positive: OwnerWorkflow, tmp_path: Path
) -> None:
    """Round 3 item 2 and round 5 item 10 at run level (the validator form is fast)."""
    _Fresh.waiting, _Fresh.root = ready_positive, tmp_path
    positive = json.dumps(SUBMISSIONS["positive"][runs.STEP], ensure_ascii=False)
    failures = model_text_failures(
        cp1c.PeerBenchmarkSubmission, positive, _Fresh, verbatim=CP1C_VERBATIM
    )
    assert failures == []


# --- A4 tamper (expected.json#tamper; the CP-DR rev 4 recipe) -----------------------------------


def _forge(store_path: Path, receipt_path: Path) -> tuple[Execution, OwnerRunReceipt]:
    """`expected.tamper.recipe`: the position 2 -> 1, then every hash that names it rewritten
    (blob, snapshot, head, attempt, receipt head, the settling submission record, the seal)."""
    tamper = EXPECTED["tamper"]
    store = Execution(store_path)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_bytes())
    snapshot = store.read()
    old = _head(store, MODULE)
    module = store.head_module(old)
    target = next(f for f in module.facts if f.fact_id == tamper["target_fact"])
    assert stage1._exact(target.amount) == tamper["from"].split()[0]
    amount = Decimal(tamper["to"].split()[0])
    forged = Module.model_validate(
        module.model_copy(
            update={
                "facts": tuple(
                    f.model_copy(update={"amount": amount}) if f.fact_id == target.fact_id else f
                    for f in module.facts
                )
            }
        ).model_dump()
    )
    new_sha = store._store(forged.model_dump_json())
    assert new_sha == forged.content_hash()
    assert head_of(forged, cp1c.QUALIFICATION).result_sha256 == new_sha
    new_snapshot = snapshot.model_copy(
        update={
            "heads": tuple(
                h.model_copy(update={"result_sha256": new_sha}) if h.module_id == MODULE else h
                for h in snapshot.heads
            ),
            "attempts": tuple(
                a.model_copy(update={"result_sha256": new_sha})
                if a.result_sha256 == old.result_sha256
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


def test_a4_a_forged_position_reaches_the_probe_and_is_refused_there(
    positive: Closed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutil.copytree(positive[0], tmp_path / "forged")
    store, receipt = _forge(tmp_path / "forged", positive[1])
    ow._verify_audit(store, receipt)  # everything upstream of the probe passes on the copy ...
    reached: list[str] = []

    def spy(executed: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        reached.append(attempt.module_id)
        cp1c.probe(executed, snapshot, attempt)

    monkeypatch.setitem(ow._PROBES, MODULE, spy)
    with pytest.raises(WorkflowError) as caught:  # ... and the CP-1C probe refuses it
        ow.verify_owner_run_receipt(store, receipt)
    assert caught.value.code == "identity_mismatch"
    assert reached == [MODULE]


def test_a4_an_edited_step_output_is_caught_by_the_blob_hash(
    positive: Closed, tmp_path: Path
) -> None:
    shutil.copytree(positive[0], tmp_path / "store")
    store = Execution(tmp_path / "store")
    attempt = _attempts(store)[0]
    blob = tmp_path / "store" / "blobs" / (attempt.steps[0].output_sha256 or "")
    blob.write_bytes(blob.read_bytes() + b" ")
    with pytest.raises(WorkflowError) as caught:
        ow.verify_owner_run_receipt(store, _receipt(positive))
    assert caught.value.code == "identity_mismatch"


# --- A7 D8 and the bindings on the settled heads; D3 open -----------------------------------------


@pytest.mark.parametrize("case", stage1.CASES)
def test_a7_tables_validate_and_the_bindings_place_every_settled_table(
    case: str, request: pytest.FixtureRequest
) -> None:
    store = _verify(request.getfixturevalue(case))
    module = store.head_module(_head(store, MODULE))
    validate_tables(module.tables, module.facts)
    mine = next(m for m in registry.modules() if m.module_id == MODULE).table_ids
    assert {t.table_id for t in module.tables} <= set(mine)
    view = View(
        run=store.pack().run,
        mode="accepted",
        modules=(
            ModuleView(
                module_id=MODULE,
                title="Peer benchmark",
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


@pytest.mark.skip(reason="blocked on G2 (Stage 3): render_owner_slice and the DeliveryScope row")
def test_a7_g2_renders_the_peer_positioning_block() -> None:
    """DeliveryScope(scope_id="cp1c-fp03-peers", pathway="relative_value",
    requested_modules=("CP-1C",), sections=("peer-positioning",), rails=("evidence",
    "limitations")) renders peer-positioning populated (lease Rendered sections)."""


@pytest.mark.parametrize("case", stage1.CASES)
def test_d3_the_reader_exposes_the_pinned_facts_of_the_genuine_head(
    case: str, request: pytest.FixtureRequest
) -> None:
    """No consumer exists (D3 open): the reader is exercised here, never as consumption."""
    store = _verify(request.getfixturevalue(case))
    head = _head(store, MODULE)
    module = store.head_module(head)
    read = cp1c.cp1c_reader(store, head)
    assert (read.status, read.head_sha256, read.limitations) == (
        head.status,
        head.result_sha256,
        module.limitations,
    )
    by_id = {f.fact_id: f for f in module.facts}
    assert [f.fact_id for f in read.facts] == list(cp1c.READER_FACTS)
    assert all(f == by_id[f.fact_id] for f in read.facts)
