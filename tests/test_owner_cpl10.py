"""CP-L10 store runs through `OwnerWorkflow` (lease Acceptance 1-5; brief section 7).

The two RefusedBegin cases need no CP-1 promotion and run in seconds. Everything else forks one
genuine CP-0/CP-1 promotion (about 80 s, DEFERRED to Stage 5 with the other slow runs):
the positive and limited runs cell for cell, the verifier-level tamper, `stale_binding`, submit
before `read_inputs`, `invoke` refused with one ok read and no pack call, the blocked walk with a
receipt, "store bytes unchanged", and the settled navigator state. Front Page blocks and rail
population are blocked on G2 (Stage 3). Fast checks live in `tests/test_connect_cpl10.py`.
"""

import hashlib
import importlib
import json
import shutil
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from cpl10_runs import (
    ALL_GAPS,
    LIMITED,
    POSITIVE,
    literal,
    make_pack,
    oracle,
    promoted,
    start,
)

from deploy_vii import report_view
from deploy_vii.contracts import Citation, Fact, Module, Run, validate_tables
from deploy_vii.execution import (
    Execution,
    NotAuthorized,
    head_of,
    inherited_limitations,
)
from deploy_vii.preparation import PreparedPack
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow
from deploy_workflow.owners import cpl10
from deploy_workflow.owners.blank import one_per_page
from deploy_workflow.workflow import WorkflowError

fw: Any = importlib.import_module("test_financial_workflow")
s1a_runs: Any = importlib.import_module("s1a_runs")
s1a: Any = importlib.import_module("test_owner_s1a")
EXPECTED: dict[str, Any] = oracle()["expected"]
SUBMISSIONS: dict[str, Any] = oracle()["submissions"]
MANIFEST: dict[str, Any] = oracle()["manifest"]
SYNTHETIC = "Synthetic case; not real issuer qualification"


# --- the two RefusedBegin cases (fast: no CP-1 promotion) -------------------------------------


def _refused_pack() -> PreparedPack:
    run = Run.model_validate_json(json.dumps(MANIFEST["cases"]["refused"]["run"]))
    return PreparedPack(run=run, sources=fw.make_pack(gap=True).sources)


def test_cp1_missing_is_the_frozen_refused_begin(tmp_path: Path) -> None:
    pack = _refused_pack()
    workflow = OwnerWorkflow.create(tmp_path / "store", pack)
    review = json.loads(fw.readiness(pack, gap=True))
    refused = SUBMISSIONS["refused"]
    review["consumers"] = [refused["cp0_consumer_row_cp1"], refused["cp0_consumer_row_cpl10"]]
    review["gaps"] = [refused["gap_row"]]
    fw.read_sources(workflow, gap=True)
    outcome = workflow.submit_review(json.dumps(review))
    assert outcome["status"] == "valid", outcome
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    want = EXPECTED["refused"]
    assert [a.module_id for a in snapshot.attempts] == want["attempts"] == ["CP-0"]
    assert [h.module_id for h in snapshot.heads] == want["heads"]
    cp0 = store.head_module(snapshot.heads[0])
    assert snapshot.heads[0].status == want["cp0"]["settled_status"]
    assert [[c.row_id, c.text] for c in snapshot.heads[0].commands] == [
        ["CP-1", "DO NOT RUN"],
        ["CP-L10", "DO NOT RUN"],
    ]
    assert cp0.module_id == "CP-0"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [r.module_id for r in receipt.refusals] == ["CP-1"]
    assert receipt.refusals[0].reason == str(NotAuthorized("CP-1", ("DO NOT RUN",)))
    assert receipt.refusals[0].reason == want["refused_begins"][0]["reason"]
    assert not [a for a in snapshot.attempts if a.module_id == "CP-L10"]
    assert not [h for h in snapshot.heads if h.module_id == "CP-L10"]
    ow.verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)


def test_blocked_cp1_is_a_retained_refusal_of_cpl10(tmp_path: Path) -> None:
    """The lease statement (blocked_cp1_refusal), built in code on the financial pack: CP-1
    blocked after two invalid attempts, then `begin("CP-L10")` is refused as blocked."""
    pack = make_pack()
    workflow, _ = start(tmp_path)
    fw.read_sources(workflow)
    s1a_runs_literal = json.loads(fw.readiness(pack))
    s1a_runs_literal["consumers"].append(SUBMISSIONS["cp0_consumer_row_cpl10"])
    assert workflow.submit_review(json.dumps(s1a_runs_literal))["status"] == "valid"
    for _attempt in (0, 1):
        for _repair in (0, 1):
            fw.read_sources(workflow)
            workflow.submit_review("{}")
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    cp1 = [a for a in snapshot.attempts if a.module_id == "CP-1"]
    assert [a.number for a in cp1] == [0, 1]
    head = next(h for h in snapshot.heads if h.module_id == "CP-1")
    assert head.status == "blocked"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [(r.module_id, r.reason) for r in receipt.refusals] == [("CP-L10", ow.BLOCKED_EDGE)]
    assert not [a for a in snapshot.attempts if a.module_id == "CP-L10"]
    assert not [h for h in snapshot.heads if h.module_id == "CP-L10"]
    ow.verify_owner_run_receipt(store, receipt)


# --- one genuine promotion, forked (slow: deferred) -------------------------------------------


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[OwnerWorkflow, PreparedPack]]:
    yield promoted(tmp_path_factory.mktemp("cpl10-promoted"))


def _fork(base: tuple[OwnerWorkflow, PreparedPack], root: Path) -> OwnerWorkflow:
    workflow: OwnerWorkflow = s1a_runs.clone_workflow(base[0], root)
    return workflow


def _tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode() + path.read_bytes())
    return digest.hexdigest()


def _closed(
    base: tuple[OwnerWorkflow, PreparedPack], root: Path, case: str
) -> tuple[Execution, OwnerRunReceipt, str]:
    workflow = _fork(base, root)
    read = workflow.read_inputs()
    outcome = workflow.submit_review(literal(case))
    assert outcome["status"] == "valid", outcome
    receipt = workflow.write_receipt(root / "receipt.json")
    return Execution(root / "store"), receipt, read["body"]


# acceptance 1 and 2, cell for cell ---------------------------------------------------------


def _expected_text(text: str | None, heads: dict[str, Any]) -> str | None:
    if text is None:
        return None
    for marker, value in (
        ("{{CP0_RESULT_SHA256}}", heads["CP-0"].result_sha256),
        ("{{CP1_RESULT_SHA256}}", heads["CP-1"].result_sha256),
        ("{{CP0_STATUS_WORD}}", "With limitations"),
        ("{{CP1_STATUS_WORD}}", "With limitations"),
    ):
        text = text.replace(marker, value)
    return text


def _cites(cp1: dict[str, Fact], labels: list[str]) -> tuple[Citation, ...]:
    return one_per_page(tuple(c for label in labels for c in cp1[label].citations))


@pytest.mark.parametrize("case", [POSITIVE, LIMITED])
def test_closed_run_equals_the_oracle_cell_for_cell(
    base: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path, case: str
) -> None:
    store, receipt, view_body = _closed(base, tmp_path, case)
    want = EXPECTED["cases"][case]
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    assert {m: h.status for m, h in heads.items()} == dict.fromkeys(
        ("CP-0", "CP-1", "CP-L10"), "restricted"
    )
    # the receipt verifies and verification leaves the store bytes unchanged
    before = _tree(tmp_path)
    ow.verify_owner_run_receipt(store, receipt)
    assert _tree(tmp_path) == before
    module = store.head_module(heads["CP-L10"])
    cp1_module = store.head_module(heads["CP-1"])
    cp1 = {f.label: f for f in cp1_module.facts if f.table_id == "T4.10"}
    # inputs hash-equal to the heads
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == heads["CP-L10"].result_sha256)
    assert [(i.input_id, i.sha256) for i in attempt.inputs] == [
        ("prepared-pack", snapshot.pack_sha256),
        ("CP-0", heads["CP-0"].result_sha256),
        ("CP-1", heads["CP-1"].result_sha256),
    ]
    assert module.inputs[:-1] == attempt.inputs and module.inputs[-1].input_id == (
        "change-screen-submission"
    )
    # facts: copied cells (incl. calculation_id), run-bound TL10.1 cells, calculated cells
    got = {f.fact_id: f for f in module.facts}
    assert set(got) == {f["fact_id"] for f in want["facts"]}
    for w in want["facts"]:
        fact = got[w["fact_id"]]
        calculation_id = w.get("calculation_id")
        copied = w.get("copied_from_cp1")
        if calculation_id == "{{CP1_CALCULATION_ID}}":
            assert copied is not None
            calculation_id = cp1[copied].calculation_id
        # a copied cell keeps CP-1's own citations; a derived cell is one per (source, page)
        citations = cp1[copied].citations if copied else _cites(cp1, w.get("derives_from") or [])
        exact = w.get("amount_exact")
        assert (
            fact.label,
            fact.status,
            fact.unit,
            fact.period,
            fact.amount,
            fact.text,
            fact.decimals,
            fact.value_class,
            fact.calculation_id,
            fact.limitation,
            fact.currency,
            fact.scale,
            fact.citations,
        ) == (
            w["label"],
            w["status"],
            w.get("unit"),
            w.get("period"),
            None if exact is None else Decimal(exact),
            _expected_text(w.get("text"), heads),
            w.get("decimals"),
            w.get("value_class"),
            calculation_id,
            w.get("limitation"),
            w.get("currency"),
            Decimal(w.get("scale", "1")),
            citations,
        ), w["fact_id"]
    # tables, claims and their citations
    validate_tables(module.tables, module.facts)
    assert [
        (t.table_id, [c.field for c in t.columns], [list(r.fact_ids) for r in t.rows])
        for t in module.tables
    ] == [(t["table_id"], t["columns"], [r["fact_ids"] for r in t["rows"]]) for t in want["tables"]]
    assert [(c.claim_id, c.text, c.limitation) for c in module.claims] == [
        (c["claim_id"], c["text"], c["limitation"]) for c in want["claims"]
    ]
    for claim, w in zip(module.claims, want["claims"], strict=True):
        labels = [m.removeprefix("{{CP1_CITATIONS:").removesuffix("}}") for m in w["citations"]]
        assert claim.citations == _cites(cp1, labels), claim.claim_id
    # limitations: settled own list, then what the bound heads pass on
    assert list(module.limitations) == want["settled_limitations"]
    own = tuple(module.limitations)
    assert module.inherited_limitations == inherited_limitations(
        snapshot, attempt, own, store.head_module
    )
    assert SYNTHETIC in module.limitations and SYNTHETIC not in module.inherited_limitations
    # the recorded view equals the oracle on genuine heads (M1) and shows no analyst-quotable text
    tree = json.loads(view_body)
    assert tree["topics"] == want["view_topics"]
    assert tree["pair_screens"] == want["view_pair_screens"]
    reads = [r for r in receipt.input_reads if r.binding.module_id == "CP-L10"]
    assert [r.body for r in reads] == [view_body]
    # exactly one ok read before the submit, no pack call, the reader on the closed head (D3 open)
    assert [c for c in receipt.calls if c.binding.module_id == "CP-L10"] == []
    head = cpl10.cpl10_reader(store, heads["CP-L10"])
    assert dict(head.counts) == want["counts"] and head.status == "restricted"
    assert EXPECTED["consumption"].startswith("OPEN")


# tool-use refusals, order, staleness -------------------------------------------------------


def test_invoke_is_refused_with_one_ok_read_and_no_pack_call(
    base: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(base, tmp_path)
    workflow.read_inputs()
    call = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert (call["status"], call["error_code"]) == ("refused", "not_permitted")
    assert workflow.submit_review(literal(POSITIVE))["status"] == "valid"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    mine = [c for c in receipt.calls if c.binding.module_id == "CP-L10"]
    assert [(c.tool, c.status, c.error_code) for c in mine] == [
        ("read_pages", "refused", "not_permitted")
    ]
    assert len([r for r in receipt.input_reads if r.binding.module_id == "CP-L10"]) == 1
    assert not [c for c in mine if c.status == "ok"]


def test_submit_before_read_inputs_is_not_permitted(
    base: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(base, tmp_path)
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(literal(POSITIVE))
    assert caught.value.code == "not_permitted"


def test_a_snapshot_change_between_read_and_submit_is_stale(
    base: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(base, tmp_path)
    workflow.read_inputs()
    Execution(tmp_path / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(literal(POSITIVE))
    assert caught.value.code == "stale_binding"


# the blocked walk with a receipt --------------------------------------------------------------


def test_blocked_walk_through_the_workflow_verifies_and_reads_status_only(
    base: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    workflow = _fork(base, tmp_path)
    by_id = {r["id"]: r for r in SUBMISSIONS["refusals"]}
    workflow.read_inputs()
    first = workflow.submit_review(json.dumps(by_id["r01"]["payload"]))
    workflow.read_inputs()
    second = workflow.submit_review(json.dumps(by_id["r08"]["payload"]))
    assert (first["status"], second["status"]) == ("invalid", "invalid")
    assert list(second["issues"]) == EXPECTED["blocked"]["expect"]["issues_attempt_1"]
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = Execution(tmp_path / "store")
    ow.verify_owner_run_receipt(store, receipt)
    head = next(h for h in store.read().heads if h.module_id == "CP-L10")
    assert head.status == "blocked"
    module = store.head_module(head)
    assert module.tables == () and module.claims == ()
    got = cpl10.cpl10_reader(store, head)
    assert (got.status, got.result_sha256, got.topics) == ("blocked", head.result_sha256, ())


# tamper at the verifier: only cpl10.probe refuses ------------------------------------------


def test_a_consistently_forged_head_is_refused_only_by_the_probe(
    base: tuple[OwnerWorkflow, PreparedPack],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, receipt, _ = _closed(base, tmp_path, POSITIVE)
    assert s1a._verdict(store, receipt) == "accepted"
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-L10")
    module = store.result(head.result_sha256)
    facts = tuple(
        f.model_copy(update={"text": "Stable"}) if f.fact_id == "TL10.2.cash.materiality" else f
        for f in module.facts
    )
    forged_module: Module = module.model_copy(update={"facts": facts})
    store._store(forged_module.model_dump_json())
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    forged_attempt = attempt.model_copy(update={"result_sha256": forged_module.content_hash()})
    forged = snapshot.model_copy(
        update={
            "attempts": tuple(
                forged_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            ),
            "heads": tuple(
                head_of(forged_module, cpl10.QUALIFICATION) if h.module_id == "CP-L10" else h
                for h in snapshot.heads
            ),
        }
    )
    store._write(forged)
    last = receipt.submissions[-1]
    assert last.snapshot_after_sha256 == snapshot.content_hash()
    moved = last.model_copy(update={"snapshot_after_sha256": forged.content_hash()})
    s1a._swap(store, "submissions", last, moved)
    resealed = receipt.model_copy(
        update={
            "snapshot_sha256": forged.content_hash(),
            "heads": tuple(ow._settled(store, h.module_id) for h in forged.heads),
            "submissions": (*receipt.submissions[:-1], moved),
        }
    )
    s1a._reseal(store, resealed)
    ow._verify_audit(store, resealed)  # the audit and the seal agree with the forged copy
    reached: list[str] = []
    real = ow._PROBES["CP-L10"]

    def recording(*args: Any) -> None:
        try:
            real(*args)
        except WorkflowError as error:
            reached.append(error.code)
            raise

    monkeypatch.setitem(ow._PROBES, "CP-L10", recording)
    assert s1a._verdict(store, resealed) == "identity_mismatch"
    assert reached == ["identity_mismatch"]  # no earlier check refused: the probe did


# acceptance 6, the settled state of the navigator -------------------------------------------


def test_navigator_names_the_settled_screen(
    base: tuple[OwnerWorkflow, PreparedPack], tmp_path: Path
) -> None:
    store, _, _ = _closed(base, tmp_path, POSITIVE)
    rows = {r.module_id: r for r in report_view.navigator(store.view())}
    assert (rows["CP-L10"].number, rows["CP-L10"].word) == (3, "With limitations")
    assert ALL_GAPS  # the driver's marker, kept in sync with the literal
    shutil.rmtree(tmp_path / "store")
