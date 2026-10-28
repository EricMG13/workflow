"""G1 acceptance: the generic owner workflow equals the financial slice and refuses honestly."""

import importlib
import json
import shutil
from collections.abc import Iterator, Mapping
from copy import copy
from dataclasses import replace
from pathlib import Path
from threading import Lock
from typing import Any

import pytest

from deploy_vii.contracts import Run
from deploy_vii.cp1_workflow import CP1_PROMOTION, CP1Handoff
from deploy_vii.cp_model_workflow import verify_cp_model_publication
from deploy_vii.downstream_readiness import DownstreamReport
from deploy_vii.execution import Execution, NotAuthorized
from deploy_vii.preparation import PreparedPack
from deploy_workflow.workflow import WorkflowError

fw: Any = importlib.import_module("test_financial_workflow")


def _owner() -> Any:
    return importlib.import_module("deploy_workflow.owner_workflow")


def _tree(*roots: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes()
        for root in roots
        if root.exists()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.fixture(scope="module")
def cases(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Build the financial and owner runs once per module; tests copy, never mutate."""
    owner = _owner()
    base = tmp_path_factory.mktemp("g1-equivalence")
    fin_root = base / "financial"
    fw.completed_financial_case(fin_root)
    own_root = base / "owner"
    own_root.mkdir()
    patch = pytest.MonkeyPatch()

    def start(root: Path, gap: bool = False) -> Any:
        pack = fw.make_pack(gap)
        return owner.OwnerWorkflow.create(
            root / "store", pack, publication_directory=root / "model"
        ), pack

    patch.setattr(fw, "start", start)
    try:
        workflow = fw.promoted_case(own_root)
    finally:
        patch.undo()
    promoted = base / "promoted"
    shutil.copytree(own_root / "store", promoted / "store")
    template = copy(workflow)
    for name in ("_calls", "_reads", "_submissions", "_publications", "_epoch_calls"):
        setattr(template, name, list(getattr(workflow, name)))
    template._limits = workflow._limits.copy()
    published = workflow.publish()
    receipt = workflow.write_receipt(own_root / "owner-receipt.json")
    return {
        "promoted": promoted,
        "template": template,
        "fin": fin_root,
        "own": own_root,
        "publish": published,
        "receipt": receipt,
    }


def _copy_owner(cases: dict[str, Any], destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("store", "model"):
        shutil.copytree(cases["own"] / name, destination / name)
    return destination


def _heads(root: Path) -> dict[str, str]:
    return {h.module_id: h.result_sha256 for h in Execution(root / "store").read().heads}


def test_equivalence_positive(cases: dict[str, Any]) -> None:
    fin, own = cases["fin"], cases["own"]
    for name in ("model.html", "calculation.json"):
        assert (fin / "model" / name).read_bytes() == (own / "model" / name).read_bytes()
    a = json.loads((fin / "model" / "receipt.json").read_text())
    b = json.loads((own / "model" / "receipt.json").read_text())
    a.pop("ticket_id")
    b.pop("ticket_id")
    assert a == b
    assert _heads(fin) == _heads(own)
    assert set(_heads(own)) == {"CP-0", "CP-1", "CP-MODEL"}

    store = Execution(own / "store")
    snapshot = store.read()
    heads = {h.module_id: h for h in snapshot.heads}
    assert heads["CP-0"].status == "restricted"
    assert heads["CP-1"].status == "restricted"
    attempt = next(a for a in snapshot.attempts if a.module_id == "CP-1")
    assert tuple(s.step_id for s in attempt.steps) == CP1_PROMOTION
    downstream = DownstreamReport.model_validate_json(
        store.step_output(attempt.steps[3].output_sha256 or "")
    )
    assert downstream.model.status == "ready"
    assert len(downstream.inputs.model.readiness.selected_quarters) == 4
    receipt = cases["receipt"]
    published = next(p for p in receipt.publications if p.status == "published")
    assert set(published.files) == {"model.html", "calculation.json", "receipt.json"}
    assert receipt.model.files == published.files
    handoff = CP1Handoff.model_validate_json(
        store.step_output(attempt.steps[-1].output_sha256 or "")
    )
    confidence = handoff.quality.confidence
    # 59 is the independent formula of quality_ready_case; MODULES.csv CP-1 row.
    assert json.loads((own / "qa-expected.json").read_text())["score"] == 59
    assert confidence.confidence_score == 59
    assert confidence.qa_status == "Restricted"
    assert confidence.confidence_band == "Low"
    assert verify_cp_model_publication(store, own / "model") == ()
    assert cases["publish"]["status"] == "ok"
    _owner().verify_owner_run_receipt(store, receipt, publication_directory=own / "model")


def test_equivalence_gap(tmp_path: Path) -> None:
    owner = _owner()
    pack = fw.make_pack(gap=True)
    workflow = owner.OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    fw.read_sources(workflow, gap=True)
    outcome = workflow.submit_review(fw.readiness(pack, gap=True))
    assert outcome["status"] == "valid"
    with pytest.raises(WorkflowError) as premature:
        workflow.write_receipt(tmp_path / "premature.json")
    assert premature.value.code == "not_permitted"
    assert workflow.publish()["status"] == "refused"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    assert [a.module_id for a in snapshot.attempts] == ["CP-0"]
    assert [(h.module_id, h.status) for h in snapshot.heads] == [("CP-0", "restricted")]
    assert len(receipt.refusals) == 1
    assert receipt.refusals[0].module_id == "CP-1"
    try:
        from deploy_vii.execution import current_inputs

        current_inputs(snapshot, "CP-1")
    except NotAuthorized as error:
        assert receipt.refusals[0].reason == str(error)
    else:
        raise AssertionError("CP-1 was authorized")
    assert len(receipt.publications) == 1
    publication = receipt.publications[0]
    assert (publication.status, publication.ticket_id, publication.files) == ("refused", None, {})
    assert not (tmp_path / "model").exists()
    owner.verify_owner_run_receipt(store, receipt, publication_directory=None)


def _requested(pack: PreparedPack, modules: tuple[str, ...]) -> PreparedPack:
    run = Run.model_validate_json(
        json.dumps({**json.loads(pack.run.model_dump_json()), "requested_modules": modules})
    )
    return PreparedPack(run=run, sources=pack.sources)


@pytest.mark.parametrize("modules", [("CP-1", "CP-2", "CP-MODEL"), ("CP-NOT-A-MODULE",)])
def test_unsupported_and_unknown_selection_write_nothing(
    tmp_path: Path, modules: tuple[str, ...]
) -> None:
    pack = _requested(fw.make_pack(), modules)
    with pytest.raises(WorkflowError) as caught:
        _owner().OwnerWorkflow.create(
            tmp_path / "store", pack, publication_directory=tmp_path / "model"
        )
    assert caught.value.code == "not_permitted"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("where", ["none", "exists", "same", "inside"])
def test_bad_publication_directory_writes_nothing(tmp_path: Path, where: str) -> None:
    store = tmp_path / "store"
    directory = {
        "none": None,
        "exists": tmp_path,
        "same": store,
        "inside": store / "model",
    }[where]
    with pytest.raises(WorkflowError) as caught:
        _owner().OwnerWorkflow.create(store, fw.make_pack(), publication_directory=directory)
    assert caught.value.code == "not_permitted"
    assert not store.exists()


def test_snapshot_change_between_read_and_submit_refuses(tmp_path: Path) -> None:
    workflow = _owner().OwnerWorkflow.create(
        tmp_path / "store", fw.make_pack(), publication_directory=tmp_path / "model"
    )
    pack = fw.make_pack()
    fw.read_sources(workflow)
    store = Execution(tmp_path / "store")
    ticket = store.read().attempts[0].ticket_id
    store.interrupt(ticket, "external change between read and submit")
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(fw.readiness(pack))
    assert caught.value.code == "stale_binding"


def test_tamper_and_foreign_store_refuse(tmp_path: Path, cases: dict[str, Any]) -> None:
    owner = _owner()
    receipt = cases["receipt"]
    root = _copy_owner(cases, tmp_path / "audit")

    def verify(r: Any = receipt) -> None:
        owner.verify_owner_run_receipt(
            Execution(root / "store"), r, publication_directory=root / "model"
        )

    verify()
    call = next((root / "store/owner-run-audit/calls").iterdir())
    original = call.read_bytes()
    call.write_bytes(original.replace(b'"status":"ok"', b'"status":"error"', 1))
    assert call.read_bytes() != original
    with pytest.raises(WorkflowError) as tampered:
        verify()
    assert tampered.value.code == "identity_mismatch"
    call.write_bytes(original)
    verify()
    changed = receipt.model_copy(update={"participant": "someone-else"})
    with pytest.raises(WorkflowError) as relabelled:
        verify(changed)
    assert relabelled.value.code == "identity_mismatch"
    foreign = tmp_path / "foreign"
    gap = owner.OwnerWorkflow.create(
        foreign / "store", fw.make_pack(gap=True), publication_directory=foreign / "model"
    )
    assert gap is not None
    with pytest.raises(WorkflowError) as mismatched:
        owner.verify_owner_run_receipt(
            Execution(foreign / "store"), receipt, publication_directory=root / "model"
        )
    # A different run fails the first verifier comparison, as the reference does
    # (financial_workflow.py:868-874 raises stale_binding), not the identity checks.
    assert mismatched.value.code == "stale_binding"


def test_verifier_is_read_only(tmp_path: Path, cases: dict[str, Any]) -> None:
    root = _copy_owner(cases, tmp_path / "ro")
    before = _tree(root / "store", root / "model")
    assert before
    _owner().verify_owner_run_receipt(
        Execution(root / "store"), cases["receipt"], publication_directory=root / "model"
    )
    assert _tree(root / "store", root / "model") == before


def test_publish_failure_outside_value_error_still_quarantines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cases: dict[str, Any]
) -> None:
    """Mirrors test_finish_and_interrupt_failure_still_quarantines (lease: publish quarantines)."""
    template = cases["template"]
    workflow = copy(template)
    shutil.copytree(cases["promoted"] / "store", tmp_path / "store")
    workflow._store = Execution(tmp_path / "store")
    workflow._publication_directory = tmp_path / "model"
    workflow._operation = Lock()
    for name in ("_calls", "_reads", "_submissions", "_publications", "_epoch_calls"):
        setattr(workflow, name, list(getattr(template, name)))
    workflow._limits = template._limits.copy()

    def unavailable_finish(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Causal journal write failure")

    monkeypatch.setattr(workflow._store, "finish", unavailable_finish)
    assert workflow.publish()["status"] == "refused"
    assert not (tmp_path / "model").exists()
    assert len(list(tmp_path.glob("model.failed-*"))) == 1
    assert workflow._publications[-1].status == "failed"
    assert "interruption failed" in (workflow._publications[-1].reason or "")
    with pytest.raises(WorkflowError) as unsealed:
        workflow.write_receipt(tmp_path / "refused.json")
    assert unsealed.value.code == "not_permitted"
    assert not (tmp_path / "refused.json").exists()


def test_analytical_spec_must_equal_reference(tmp_path: Path) -> None:
    owner = _owner()
    cp0 = owner.OWNER_SPECS["CP-0"]
    steps = tuple(replace(step, rules=False) for step in cp0.steps)
    weakened = {**owner.OWNER_SPECS, "CP-0": replace(cp0, steps=steps)}
    with pytest.raises(WorkflowError) as caught:
        owner.OwnerWorkflow.create(
            tmp_path / "store",
            fw.make_pack(),
            specs=weakened,
            publication_directory=tmp_path / "model",
        )
    assert caught.value.code == "not_permitted"
    assert list(tmp_path.iterdir()) == []


def test_rejected_then_blocked_walk_retains_refusal(tmp_path: Path) -> None:
    owner = _owner()
    pack = fw.make_pack()
    workflow = owner.OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    good = json.loads(fw.readiness(pack))
    invalid = json.dumps({**good, list(good)[-1]: None})
    fw.read_sources(workflow)
    first = workflow.submit_review(invalid)
    assert first["status"] != "valid" and first["next_step"] is not None
    attempts = Execution(tmp_path / "store").read().attempts
    assert [(a.module_id, a.number) for a in attempts] == [("CP-0", 0), ("CP-0", 1)]
    fw.read_sources(workflow)
    second = workflow.submit_review(invalid)
    assert second["refusal"] == "cp1_blocked"
    assert second["next_step"] is None
    snapshot = Execution(tmp_path / "store").read()
    assert [(a.module_id, a.number) for a in snapshot.attempts] == [("CP-0", 0), ("CP-0", 1)]
    assert [(h.module_id, h.status) for h in snapshot.heads] == [("CP-0", "blocked")]
    assert [r.module_id for r in workflow._refusals] == ["CP-1"]
    assert workflow.publish()["error_code"] == "cp1_blocked"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert receipt.refusals[0].module_id == "CP-1"
    owner.verify_owner_run_receipt(
        Execution(tmp_path / "store"), receipt, publication_directory=None
    )


def test_run_binds_to_reference_specs_not_callers_mapping(tmp_path: Path) -> None:
    """Mutating the caller's mapping after create must not switch off the evidence rules."""
    owner = _owner()
    with pytest.raises(TypeError):
        owner.OWNER_SPECS["CP-1"] = owner.OWNER_SPECS["CP-1"]
    specs = dict(owner.OWNER_SPECS)
    pack = fw.make_pack()
    workflow = owner.OwnerWorkflow.create(
        tmp_path / "store", pack, specs=specs, publication_directory=tmp_path / "model"
    )
    cp1 = specs["CP-1"]
    specs["CP-1"] = replace(cp1, steps=tuple(replace(s, rules=False) for s in cp1.steps))
    fw.read_sources(workflow)
    assert workflow.submit_review(fw.readiness(pack))["status"] == "valid"
    # Uncited pages: the reference rules refuse a source_context read with no tool calls.
    outcome = workflow.submit_review(fw.context(pack))
    assert outcome["status"] == "refused"
    assert any("read_pages" in issue for issue in outcome["issues"])


def _shadow_publish(store: Execution, *, output: Path) -> Any:
    raise AssertionError("a non-reference publisher must never be reachable")


def test_deterministic_and_unplanned_specs_must_equal_reference(
    tmp_path: Path,
) -> None:
    owner = _owner()
    reference = owner.OWNER_SPECS
    shadow = owner.OwnerSpec("CP-X", (), None, "deterministic", _shadow_publish)
    cases = {
        "publisher replaced": {
            **reference,
            "CP-MODEL": replace(reference["CP-MODEL"], publish=_shadow_publish),
        },
        "unplanned deterministic first": {"CP-X": shadow, **reference},
        "unplanned deterministic last": {**reference, "CP-X": shadow},
        "unplanned key without reference entry": {**reference, "CP-X": None},
    }
    for label, specs in cases.items():
        root = tmp_path / label.replace(" ", "-")
        root.mkdir()
        with pytest.raises(WorkflowError) as caught:
            owner.OwnerWorkflow.create(
                root / "store",
                fw.make_pack(gap=True),
                specs=specs,
                publication_directory=root / "model",
            )
        assert caught.value.code == "not_permitted", label
        assert list(root.iterdir()) == [], label


class _DishonestSpecs(Mapping[str, Any]):
    """get() returns the reference spec; item access lies that CP-MODEL is analytical."""

    def __init__(self, reference: Mapping[str, Any], liar: Any) -> None:
        self._reference, self._liar = reference, liar

    def get(self, key: str, default: Any = None) -> Any:
        return self._reference.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._liar if key == "CP-MODEL" else self._reference[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._reference)

    def __len__(self) -> int:
        return len(self._reference)


def test_create_reads_kind_from_reference_not_callers_mapping(tmp_path: Path) -> None:
    """A mapping that lies through __getitem__ must not skip the publication-directory refusal."""
    owner = _owner()
    reference = owner.OWNER_SPECS
    specs = _DishonestSpecs(reference, replace(reference["CP-MODEL"], kind="analytical"))
    with pytest.raises(WorkflowError) as caught:
        owner.OwnerWorkflow.create(
            tmp_path / "store", fw.make_pack(), specs=specs, publication_directory=None
        )
    assert caught.value.code == "not_permitted"
    assert list(tmp_path.iterdir()) == []
