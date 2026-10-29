"""CP-2E store runs: the closed two-module run over the oracle, CP-0 then CP-2E.

DEFERRED to Stage 5 (brief step 7): written, not run at Stage 2. Expectations come from
`cases/cp2e-owner/expected.json` only. The D3 test pins what the reader exposes; consumption is
OPEN, so nothing here claims completion. The tamper, stale_binding, blocked and begin-refused
cases are written below (`test_tamper_is_refused_by_the_probe_alone`,
`test_a_snapshot_change_between_read_and_submit_is_stale`,
`test_the_blocked_case_blocks_after_two_invalid_attempts`,
`test_begin_is_refused_when_cp0_is_blocked`).
"""

import hashlib
import importlib
import json
import shutil
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from cp2e_runs import (
    CASES,
    cp2e_closed,
    drive_cp0,
    drive_cp2e,
    literal,
    make_pack,
    oracle,
    read_cited,
    search,
    start,
    submit_valid,
)
from test_method_cp2e import _mutated

from deploy_vii.contracts import Span
from deploy_vii.execution import Execution, head_of
from deploy_vii.live.tools import cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow, verify_owner_run_receipt
from deploy_workflow.owners import cp2e
from deploy_workflow.workflow import WorkflowError

ow: Any = importlib.import_module("deploy_workflow.owner_workflow")  # private helpers
EXPECTED: dict[str, Any] = oracle()["expected"]
SUBMISSIONS: dict[str, Any] = oracle()["submissions"]


@dataclass
class Closed:
    case: str
    root: Path
    store: Execution
    receipt: OwnerRunReceipt
    expected: dict[str, Any]


@pytest.fixture(scope="module", params=CASES)
def closed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    case: str = request.param
    root = tmp_path_factory.mktemp(f"cp2e-{case}")
    store_path, receipt_path = cp2e_closed(case, root)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_bytes())
    return Closed(case, root, Execution(store_path), receipt, EXPECTED["cases"][case])


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def test_plan_heads_and_status(closed: Closed) -> None:
    assert [h.module_id for h in closed.store.read().heads] == EXPECTED["plan"]["plan"]
    assert _head(closed.store, "CP-2E").status == closed.expected["status"]


def test_inputs_are_the_pack_cp0_and_the_submission_tail(closed: Closed) -> None:
    module = closed.store.head_module(_head(closed.store, "CP-2E"))
    assert [i.input_id for i in module.inputs] == closed.expected["module_inputs"]
    cp0 = _head(closed.store, "CP-0")
    assert next(i for i in module.inputs if i.input_id == "CP-0").sha256 == cp0.result_sha256


def test_tables_claims_and_limitations_equal_the_oracle(closed: Closed) -> None:
    module = closed.store.head_module(_head(closed.store, "CP-2E"))
    layouts = [
        t.model_dump(mode="json", exclude={"rows": {"__all__": {"row_kind"}}}, exclude_none=True)
        for t in module.tables
    ]
    assert layouts == closed.expected["module_tables"]
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in closed.expected["claims"]]
    synthetic = "Synthetic case; not real issuer qualification"
    own = list(dict.fromkeys([*closed.expected["own_limitations"], synthetic]))
    assert list(module.limitations) == own
    # inherited: the CP-0 limitations the oracle lists, without any that are own (settle's rule)
    assert list(module.inherited_limitations) == [
        t for t in closed.expected["inherited_limitations"] if t not in own
    ]


def test_the_receipt_verifies_and_the_store_is_unchanged(closed: Closed) -> None:
    before = {p: p.read_bytes() for p in sorted(closed.root.rglob("*")) if p.is_file()}
    verify_owner_run_receipt(closed.store, closed.receipt)
    assert before == {p: p.read_bytes() for p in sorted(closed.root.rglob("*")) if p.is_file()}


def test_tool_use_precedes_the_submit(closed: Closed) -> None:
    required = closed.expected["tool_use_required"]
    binding = next(
        r.binding.binding
        for r in closed.receipt.submissions
        if r.binding.binding.module_id == "CP-2E"
    )
    calls = [c for c in closed.receipt.calls if c.binding == binding and c.status == "ok"]
    pages = {
        (c.arguments["source_id"], f"page:{n}")
        for c in calls
        if c.tool == "read_pages"
        for n in range(c.arguments["first_page"], c.arguments["last_page"] + 1)
    }
    assert {tuple(p) for p in required["read_pages_cover"]} <= pages
    assert sum(c.tool == "search_pack" for c in calls) >= required["search_pack_min"]
    assert required["read_inputs_calls"] == 0
    assert not [r for r in closed.receipt.input_reads if r.binding == binding]


def test_extract_statements_and_read_inputs_are_refused(tmp_path: Path) -> None:
    workflow, pack = start("positive", tmp_path)
    drive_cp0(workflow, pack, "positive")
    refused = workflow.invoke("extract_statements", {"source_id": "financial"})
    assert refused["error_code"] == "not_permitted"
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.read_inputs()


@pytest.mark.parametrize("row", EXPECTED["tool_use_refusals"], ids=lambda r: r["id"])
def test_journaled_tool_use_refusals(row: dict[str, Any], tmp_path: Path) -> None:
    source = next(r for r in SUBMISSIONS["tool_use_refusals"] if r["id"] == row["id"])
    workflow, pack = start("positive", tmp_path)
    drive_cp0(workflow, pack, "positive")
    for sid, loc in source["reads"]:
        number = int(loc.split(":")[1])
        workflow.invoke("read_pages", {"source_id": sid, "first_page": number, "last_page": number})
    if source["searches"]:
        workflow.invoke("search_pack", {"query": "hedge", "source_id": "financial"})
    outcome = workflow.submit_review(literal("positive", "macro_fx"))
    assert outcome["status"] == "invalid"
    assert row["issue"] in outcome["issues"]


# --- D3 (OPEN): the reader exposes what the lease pins; no completion is claimed ------------------
def test_d3_reader_exposes_the_pinned_values_of_the_settled_head(closed: Closed) -> None:
    head = _head(closed.store, "CP-2E")
    read = cp2e.cp2e_reader(closed.store, head)
    assert read.head_sha256 == head.result_sha256
    assert read.status == closed.expected["status"]
    if closed.case == "positive":
        pinned = EXPECTED["consumption"]["reader_pinned"]["positive_values"]
        assert read.floating_debt.amount == Decimal(pinned["floating"]["amount"])
        assert read.shocks[0].added_interest.amount == Decimal(
            pinned["first_shock_gross"]["amount"]
        )
        assert read.shocks[0].cov_after.amount == Decimal(pinned["first_shock_cov_after"]["amount"])
    assert EXPECTED["consumption"]["status"] == "OPEN"


# --- fix round 1, M2: the lease's acceptance store tests ------------------------------------------
def _ready(tmp_path: Path, pack: PreparedPack | None = None) -> OwnerWorkflow:
    """CP-0 settled, CP-2E begun and untouched."""
    workflow = OwnerWorkflow.create(tmp_path / "store", pack or make_pack("positive"))
    drive_cp0(workflow, pack or make_pack("positive"), "positive")
    return workflow


def _verdict(store: Execution, receipt: OwnerRunReceipt) -> str:
    try:
        verify_owner_run_receipt(store, receipt)
    except WorkflowError as error:
        return error.code
    return "accepted"


def _swap(store: Execution, kind: str, old: Any, new: Any) -> None:
    (store.directory / ow.AUDIT / kind / old.content_hash()).unlink()
    if new is not None:
        ow._retain(store, kind, new)


def _reseal(store: Execution, receipt: OwnerRunReceipt) -> None:
    seal = store.directory / ow.AUDIT / "receipt.sha256"
    seal.unlink()
    ow._put(seal, receipt.content_hash().encode())


def _forge_cov_after(closed: Closed, tmp_path: Path) -> tuple[Execution, OwnerRunReceipt]:
    """expected.tamper recipe: a copy of the closed positive store whose result Module has
    T2F.3.r01.cov_after set to the pinned forged amount, re-sealed consistently."""
    root = tmp_path / "forged"
    shutil.copytree(closed.root, root)
    store = Execution(root / "store")
    receipt = OwnerRunReceipt.model_validate_json((root / "owner-receipt.json").read_bytes())
    snapshot = store.read()
    head = _head(store, "CP-2E")
    module = store.head_module(head)
    target = EXPECTED["tamper"]["target_fact"]
    amount = Decimal(EXPECTED["tamper"]["to"]["amount"])
    facts = tuple(
        f.model_copy(update={"amount": amount}) if f.fact_id == target else f for f in module.facts
    )
    forged_module = module.model_copy(update={"facts": facts})
    assert forged_module != module and head_of(forged_module).status == head.status
    store._store(forged_module.model_dump_json())
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    forged = snapshot.model_copy(
        update={
            "attempts": tuple(
                a.model_copy(update={"result_sha256": forged_module.content_hash()})
                if a.ticket_id == attempt.ticket_id
                else a
                for a in snapshot.attempts
            ),
            "heads": tuple(
                head_of(forged_module, h.qualification) if h.module_id == "CP-2E" else h
                for h in snapshot.heads
            ),
        }
    )
    store._write(forged)
    last = receipt.submissions[-1]
    assert last.snapshot_after_sha256 == snapshot.content_hash()
    moved = last.model_copy(update={"snapshot_after_sha256": forged.content_hash()})
    _swap(store, "submissions", last, moved)
    resealed = receipt.model_copy(
        update={
            "snapshot_sha256": forged.content_hash(),
            "heads": tuple(ow._settled(store, h.module_id) for h in forged.heads),
            "submissions": (*receipt.submissions[:-1], moved),
        }
    )
    _reseal(store, resealed)
    return store, resealed


def test_the_genuine_run_verifies(closed: Closed) -> None:
    assert _verdict(closed.store, closed.receipt) == "accepted"


def test_tamper_is_refused_by_the_probe_alone(
    closed: Closed, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Acceptance 5: every check before `_PROBES` passes on the forged copy; `cp2e.probe`'s
    rebuild is what refuses it (a no-op probe would let it through)."""
    if closed.case != "positive":
        pytest.skip("the recipe is stated on the positive case")
    store, receipt = _forge_cov_after(closed, tmp_path)
    ow._verify_audit(store, receipt)  # the audit and the seal agree with the forged receipt
    forged = store.head_module(_head(store, "CP-2E"))
    assert next(
        f for f in forged.facts if f.fact_id == EXPECTED["tamper"]["target_fact"]
    ).amount == (Decimal(EXPECTED["tamper"]["to"]["amount"]))
    with monkeypatch.context() as patch:
        patch.setitem(ow._PROBES, "CP-2E", lambda *_args: None)
        assert _verdict(store, receipt) == "accepted"
    snapshot = store.read()
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-2E")
    with pytest.raises(WorkflowError) as caught:
        cp2e.probe(store, snapshot, attempt)
    assert caught.value.code == "identity_mismatch"
    assert _verdict(store, receipt) == "identity_mismatch"


def test_a_snapshot_change_between_read_and_submit_is_stale(tmp_path: Path) -> None:
    workflow = _ready(tmp_path)
    payload = literal("positive", "macro_fx")
    read_cited(workflow, payload)
    Execution(tmp_path / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(payload)
    assert caught.value.code == "stale_binding"


def test_the_blocked_case_blocks_after_two_invalid_attempts(tmp_path: Path) -> None:
    blocked = SUBMISSIONS["blocked"]
    expected = EXPECTED["negative_cases"]["blocked_cp2e"]
    workflow = _ready(tmp_path)
    first = drive_cp2e(
        workflow, "positive", text=json.dumps(_mutated(blocked["attempt_0"]["edits"]))
    )
    assert first["status"] == "invalid" and first["issues"][0] == expected["attempt_0_issue"]
    second = drive_cp2e(
        workflow, "positive", text=json.dumps(_mutated(blocked["attempt_1"]["edits"]))
    )
    assert second["status"] == "invalid" and second["issues"][0] == expected["attempt_1_issue"]
    store = Execution(tmp_path / "store")
    attempts = [a for a in store.read().attempts if a.module_id == "CP-2E"]
    assert [a.number for a in attempts] == [0, 1]
    assert attempts[1].repair_of == attempts[0].ticket_id
    head = _head(store, "CP-2E")
    assert head.status == "blocked"  # a blocked result is the module's head, not an accepted one
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert _verdict(store, receipt) == "accepted"


def test_begin_is_refused_when_cp0_is_blocked(tmp_path: Path) -> None:
    pack = make_pack("positive")
    workflow, _ = start("positive", tmp_path)
    review = json.loads(literal("positive", "readiness_review", pack))
    review["pack_sha256"] = "0" * 64  # a review of another pack: the validator refuses it
    payload = json.dumps(review)
    for _ in range(2):  # two invalid CP-0 attempts (each attempt needs its own reads)
        read_cited(workflow, payload)
        assert workflow.submit_review(payload)["status"] == "invalid"
    store = Execution(tmp_path / "store")
    assert _head(store, "CP-0").status == "blocked"
    assert [m for m in (a.module_id for a in store.read().attempts)] == ["CP-0", "CP-0"]
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [r.module_id for r in receipt.refusals] == ["CP-2E"]
    assert not [b for b in receipt.begins if b.module_id == "CP-2E"]
    assert _verdict(store, receipt) == "accepted"


@pytest.mark.parametrize(
    "entry", SUBMISSIONS["refusal_mutations"]["entries"], ids=lambda e: e["id"]
)
def test_each_frozen_refusal_is_journaled_as_an_invalid_step(
    entry: dict[str, Any], tmp_path: Path
) -> None:
    workflow = _ready(tmp_path)
    payload = json.dumps(_mutated(entry["edits"]))
    for page in range(1, 6):  # the whole financial source is read, so only the validator speaks
        workflow.invoke(
            "read_pages", {"source_id": "financial", "first_page": page, "last_page": page}
        )
    search(workflow, "financial", "hedge")
    outcome = workflow.submit_review(payload)
    assert outcome["status"] == "invalid"
    # the host never serves the identity source, so a page cited there is also an unread page
    unread = [
        f"Cited page not read through read_pages: {sid} {loc}"
        for sid, loc in sorted(cited_locators(payload))
        if sid != "financial"
    ]
    assert list(outcome["issues"]) == [*entry["all_issues"], *unread]
    assert outcome["issues"][0] == {r["id"]: r["issue"] for r in EXPECTED["refusals"]}[entry["id"]]


def test_the_hand_built_page_refusal_runs_on_its_pinned_page(tmp_path: Path) -> None:
    row = SUBMISSIONS["hand_built_page_refusals"][0]
    base = make_pack("positive")
    sources = []
    for source in base.sources:
        if source.source_id != "financial":
            sources.append(source)
            continue
        spans = tuple(
            Span(
                locator=sp.locator,
                text=sp.text.replace(row["page_edit"]["from"], row["page_edit"]["to"]),
            )
            if sp.locator == row["page_locator"]
            else sp
            for sp in source.spans
        )
        page = next(sp for sp in spans if sp.locator == row["page_locator"])
        assert hashlib.sha256(page.text.encode()).hexdigest() == row["page_text_sha256"]
        digest = hashlib.sha256("\f".join(sp.text for sp in spans).encode()).hexdigest()
        assert digest == row["pack_source_sha256"]
        sources.append(source.model_copy(update={"spans": spans, "sha256": digest}))
    pack = PreparedPack(run=base.run, sources=tuple(sources))
    workflow = OwnerWorkflow.create(tmp_path / "store", pack)
    # the CP-0 literal names the pack's financial hash and quotes the edited sentence
    text = (
        literal("positive", "readiness_review", pack)
        .replace(base.sources[1].sha256 or "", row["pack_source_sha256"])
        .replace(row["page_edit"]["from"], row["page_edit"]["to"])
    )
    read_cited(workflow, text)
    submit_valid(workflow, text)
    payload = json.dumps(row["payload"])
    read_cited(workflow, payload)
    search(workflow, "financial", "hedge")
    outcome = workflow.submit_review(payload)
    assert outcome["status"] == "invalid"
    expected = EXPECTED["hand_built_page_refusals"][0]
    assert list(outcome["issues"]) == [expected["issue"]]
