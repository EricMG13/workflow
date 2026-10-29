"""CP-3D Stage 2 store runs (deferred to Stage 5): the owner core through `OwnerWorkflow`.

Written with the Stage 2 build and not run there (`work/build/deferred-runs.md`). Every expected
value is read from `cases/cp3d-owner/expected.json` and the literals from `submissions.json`;
nothing is derived here. The consumption proof (D3) stays OPEN: the reader test pins what the
reader exposes and claims no consumer.
"""

import hashlib
import importlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.execution import Execution
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt
from deploy_workflow.owners import cp3d
from deploy_workflow.workflow import WorkflowError

runs: Any = importlib.import_module("cp3d_runs")
s1a: Any = importlib.import_module("s1a_runs")
connect: Any = importlib.import_module("test_connect_cp3d")
base: Any = importlib.import_module("test_method_cp3d")

ORACLE = runs.oracle()
CASES = runs.CASES


def _closed(case: str, tmp_path: Path) -> tuple[Execution, Path]:
    store, receipt = runs.cp3d_closed(case, tmp_path)
    return Execution(store), receipt


@pytest.fixture(scope="module")
def closed(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Execution, Path]]:
    return {c: _closed(c, tmp_path_factory.mktemp(f"cp3d-{c}")) for c in CASES}


@pytest.mark.parametrize("case", CASES)
def test_closed_run_settles_restricted_with_the_expected_module(
    closed: dict[str, tuple[Execution, Path]], case: str
) -> None:
    store, _ = closed[case]
    want = ORACLE["expected"]["cases"][case]
    head = runs.head_of_module(store, "CP-3D")
    module = store.head_module(head)
    assert head.status == want["status"] == "restricted"
    assert [i.input_id for i in module.inputs] == want["module_inputs"]
    cp0 = runs.head_of_module(store, "CP-0")
    assert next(i for i in module.inputs if i.input_id == "CP-0").sha256 == cp0.result_sha256
    assert [t.table_id for t in module.tables] == [t["table_id"] for t in want["tables"]]
    facts = {f.fact_id: f for f in module.facts}
    for table in want["tables"]:
        for row in table["rows"]:
            for cell in row["facts"]:
                fact = facts[cell["fact_id"]]
                assert connect._fact_view(fact) == connect._expected_view(cell), cell["fact_id"]
    assert [(c.claim_id, c.text) for c in module.claims] == [
        (c["claim_id"], c["text"]) for c in want["claims"]
    ]
    # The store's settlement (execution.settle, case_kind synthetic) adds its own synthetic-case
    # limitation to the module's and takes it off the inherited list; the oracle's lists are the
    # candidate's (a LEAD note: the oracle does not model this settlement step).
    synthetic = "Synthetic case; not real issuer qualification"
    assert list(module.limitations) == [*want["own_limitations"], synthetic]
    assert list(module.inherited_limitations) == [
        x for x in want["inherited_limitations"] if x != synthetic
    ]


@pytest.mark.parametrize("case", CASES)
def test_closed_run_receipt_verifies_and_store_bytes_are_unchanged(
    closed: dict[str, tuple[Execution, Path]], case: str
) -> None:
    store, receipt_path = closed[case]
    before = sorted(
        (p.relative_to(store.directory), p.read_bytes())
        for p in store.directory.rglob("*")
        if p.is_file()
    )
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    verify_owner_run_receipt(store, receipt)
    after = sorted(
        (p.relative_to(store.directory), p.read_bytes())
        for p in store.directory.rglob("*")
        if p.is_file()
    )
    assert before == after


@pytest.fixture(scope="module")
def after_cp0(tmp_path_factory: pytest.TempPathFactory) -> Any:
    root = tmp_path_factory.mktemp("cp3d-after-cp0")
    workflow, _ = runs.after_cp0("positive", root)
    return workflow, root


def _fork(after_cp0: Any, tmp_path: Path) -> Any:
    return s1a.clone_workflow(after_cp0[0], tmp_path / "fork")


@pytest.mark.parametrize("entry", base.MUTATIONS["entries"], ids=lambda e: e["id"])
def test_each_refusal_mutation_is_journaled_with_exactly_its_issue(
    after_cp0: Any, tmp_path: Path, entry: dict[str, Any]
) -> None:
    workflow = _fork(after_cp0, tmp_path)
    raw = base._edited(ORACLE["submissions"][base.MUTATIONS["base"]], entry["edits"])
    outcome = runs.drive_cp3d(workflow, "positive", text=json.dumps(raw))
    expected = entry["issue"]
    assert (outcome["status"], outcome["issues"]) == ("invalid", [expected])


@pytest.mark.parametrize("entry", ORACLE["submissions"]["tool_use_refusals"], ids=lambda e: e["id"])
def test_each_tool_use_case_yields_exactly_its_issues_through_rules(
    after_cp0: Any, tmp_path: Path, entry: dict[str, Any]
) -> None:
    workflow = _fork(after_cp0, tmp_path)
    raw = base._edited(ORACLE["submissions"]["positive"], entry.get("edits", []))
    for source, locator in entry["reads"]:
        page = int(locator.split(":")[1])
        call = workflow.invoke(
            "read_pages", {"source_id": source, "first_page": page, "last_page": page}
        )
        assert call["status"] == "ok"
    for _ in range(entry["searches"]):
        s1a.search(workflow, "market", runs.SEARCH_QUERY)
    outcome = workflow.submit_review(json.dumps(raw))
    assert (outcome["status"], outcome["issues"]) == ("invalid", entry["issues"])


def test_extract_statements_and_read_inputs_are_refused_not_permitted(
    after_cp0: Any, tmp_path: Path
) -> None:
    workflow = _fork(after_cp0, tmp_path)
    extract = workflow.invoke(
        "extract_statements", {"source_id": "financial", "first_page": 5, "last_page": 5}
    )
    assert (extract["status"], extract["error_code"]) == ("refused", "not_permitted")
    with pytest.raises(WorkflowError) as error:
        workflow.read_inputs()
    assert error.value.args[0] == "not_permitted"


def test_blocked_case_settles_blocked_after_two_invalid_attempts(
    after_cp0: Any, tmp_path: Path
) -> None:
    blocked = ORACLE["submissions"]["blocked"]
    workflow = _fork(after_cp0, tmp_path)
    first = base._edited(ORACLE["submissions"]["positive"], blocked["attempt_0"]["edits"])
    one = runs.drive_cp3d(workflow, "positive", text=json.dumps(first))
    assert (one["status"], one["issues"]) == ("invalid", [blocked["attempt_0"]["issue"]])
    second = base._edited(ORACLE["submissions"]["positive"], blocked["attempt_1"]["edits"])
    two = runs.drive_cp3d(workflow, "positive", text=json.dumps(second))
    assert (two["status"], two["issues"]) == ("invalid", [blocked["attempt_1"]["issue"]])
    store = Execution(tmp_path / "fork" / "store")
    assert runs.head_of_module(store, "CP-3D").status == "blocked"


@pytest.mark.parametrize("case", CASES)
def test_reader_over_the_settled_head_exposes_the_pinned_values(
    closed: dict[str, tuple[Execution, Path]], case: str
) -> None:
    """D3 stays OPEN: no consumer reads this; the reader only exposes what the oracle pins."""
    store, _ = closed[case]
    head = runs.head_of_module(store, "CP-3D")
    got = cp3d.cp3d_reader(store, head)
    assert got.head_sha256 == head.result_sha256 and got.status == head.status
    pinned = ORACLE["expected"]["consumption"]["reader_pinned_for_cp3c"]["positive_values"]
    if case == "positive":
        assert format(got.discount_margin_mid.amount, "f") == pinned["dm_mid"]
        assert format(got.intensity_mid.amount, "f") == pinned["lam_mid"]
        assert format(got.probability_mid.amount, "f") == pinned["pd_mid"]
    else:
        assert got.intensity_mid.amount is None and got.probability_mid.amount is None
    own = ORACLE["expected"]["cases"][case]["own_limitations"]
    synthetic = "Synthetic case; not real issuer qualification"
    assert list(got.own_limitations) == list(dict.fromkeys([*own, synthetic]))


def test_copy_of_a_closed_store_keeps_the_run_verifiable(
    closed: dict[str, tuple[Execution, Path]], tmp_path: Path
) -> None:
    store, receipt_path = closed["positive"]
    shutil.copytree(store.directory, tmp_path / "store")
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)


def test_begin_is_refused_when_cp0_settles_blocked_and_no_attempt_is_consumed(
    tmp_path: Path,
) -> None:
    """Lease Acceptance 5: a blocked CP-0 refuses `begin` of CP-3D (edge `block`)."""
    workflow, pack = runs.start("positive", tmp_path)
    bad = json.loads(runs.cp0_literal("positive", pack))
    bad["sources"] = []
    for _ in range(2):
        text = json.dumps(bad)
        s1a.read_cited(workflow, text)
        outcome = workflow.submit_review(text)
        assert outcome["status"] == "invalid"
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    assert runs.head_of_module(store, "CP-0").status == "blocked"
    assert [a for a in snapshot.attempts if a.module_id == "CP-3D"] == []
    assert [r.module_id for r in workflow._refusals] == ["CP-3D"]
    assert workflow._refusals[0].reason.startswith("Required upstream is unrun, stale or blocked")


def test_a_snapshot_change_between_the_last_read_and_the_submit_is_stale(
    after_cp0: Any, tmp_path: Path
) -> None:
    """Lease Acceptance 5: `stale_binding` (pattern of test_owner_s1a)."""
    workflow = _fork(after_cp0, tmp_path)
    payload = runs.literal("positive")
    s1a.read_cited(workflow, payload)
    Execution(tmp_path / "fork" / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(payload)
    assert caught.value.code == "stale_binding"


def test_probe_refuses_a_consistently_forged_step_output(
    closed: dict[str, tuple[Execution, Path]], tmp_path: Path
) -> None:
    """Lease Acceptance 6: the forgery is consistent (the forged blob is stored under its own
    hash and the attempt names that hash), so no upstream hash check refuses it and `probe` does
    (`identity_mismatch`). The genuine attempt passes the same call."""
    shutil.copytree(closed["positive"][0].directory, tmp_path / "store")
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    head = runs.head_of_module(store, "CP-3D")
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    cp3d.probe(store, snapshot, attempt)  # the genuine attempt rebuilds exactly
    step = attempt.steps[0]
    forged = (store.step_output(step.output_sha256 or "") + " ").encode()
    digest = hashlib.sha256(forged).hexdigest()
    (tmp_path / "store" / "blobs" / digest).write_bytes(forged)
    assert store.step_output(digest) == forged.decode()  # the store itself accepts the blob
    tampered = attempt.model_copy(
        update={"steps": (step.model_copy(update={"output_sha256": digest}),)}
    )
    with pytest.raises(WorkflowError) as caught:
        cp3d.probe(store, snapshot, tampered)
    assert caught.value.code == "identity_mismatch"


def test_probe_refuses_a_consistently_forged_head(
    closed: dict[str, tuple[Execution, Path]], tmp_path: Path
) -> None:
    """Lease Acceptance 6, head half: a module with one changed limitation is stored under its
    own hash and the head names it, so the store accepts it and only `probe` refuses."""
    shutil.copytree(closed["positive"][0].directory, tmp_path / "store")
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    head = runs.head_of_module(store, "CP-3D")
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    module = store.result(head.result_sha256)
    last = module.limitations[-1]
    forged = module.model_copy(
        update={"limitations": (*module.limitations[:-1], last + " (forged)")}
    )
    raw = forged.model_dump_json().encode()
    digest = hashlib.sha256(raw).hexdigest()
    (tmp_path / "store" / "blobs" / digest).write_bytes(raw)
    fhead = head.model_copy(update={"result_sha256": digest})
    fsnap = snapshot.model_copy(
        update={"heads": tuple(fhead if h == head else h for h in snapshot.heads)}
    )
    assert store.head_module(fhead) == forged  # the store accepts the forged head
    with pytest.raises(WorkflowError) as caught:
        cp3d.probe(store, fsnap, attempt)
    assert caught.value.code == "identity_mismatch"
