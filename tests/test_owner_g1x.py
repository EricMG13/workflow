"""G1-X acceptance: the owner-core protocol seams (`docs/G1X-OWNER-CORE-PROTOCOL.md` §1-§4) and
the verifier exception mapping (`docs/S1A-OWNER-RUN-LEASE.md` R4-4).

Every seam is exercised through a test-only fake owner core defined in this file and registered
by monkeypatching `owner_workflow._CORES` and the rows a module task adds (`OWNER_SPECS`,
`SUPPORTED_ANALYTICAL`, `_QUALIFICATION`, `_PROBES`, `_VIEWS`, `_PRECHECKS`, `_ENTRY_VALIDATORS`).
It is not product code. It stands for CP-3D, a real owner-only module (`registry.step_chain`
raises "has no live step contract"; plan CP-0 -> CP-3D, so no CP-1 promotion is needed), with
two invented steps:
- `g1x_sourced`: pack sources, a view, journaled rules (the CP-1C/CP-1D step shape);
- `g1x_viewed`: session-less, a view, no rules (the CP-2D/CP-L10 step shape).
The owner-only host scope is the H1 task's and not built, so the sourced step's pages are read
through `_FakeSession`, a test-only session double; CP-0 keeps the real `SourceSession`.

Expectations come from the protocol text, never from the code under test. Each run takes well
under a second.
"""

import hashlib
import importlib
import json
import shutil
from collections.abc import Callable, Iterator
from dataclasses import replace
from functools import partial
from pathlib import Path
from types import MappingProxyType, ModuleType, SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from deploy_vii.contracts import Contract, Module, Run
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Qualification,
    StepValidation,
    settle,
)
from deploy_vii.live.schema import normalise
from deploy_vii.live.submission import Submitted, _with_rules
from deploy_vii.live.tools import Seen, unread_citation_issues
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import plan, step_chain
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.host import SourceSession
from deploy_workflow.workflow import SourceEvidence, WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("s1a_runs")

MODULE = "CP-3D"
SOURCED, VIEWED = "g1x_sourced", "g1x_viewed"
STEP_IDS = (SOURCED, VIEWED)
QUALIFICATION = Qualification(implementation="implemented")
GATE_MARK = "refuse-me"
GATE_ISSUE = "Gate: the note asks to be refused"
INVALID_MARK = "invalid"
VALIDATOR_ISSUE = "Fake validator: the note is invalid"
# The product wording of the cited-page rule (`live.tools.UNREAD_PAGE`), the one the fake RULES
# reuses as the protocol tells a core to (G1-X §2).
UNREAD = "Cited page not read through read_pages: financial page:1"


# --- the test-only fake owner core ------------------------------------------------------------


class Cite(Contract):
    source_id: str
    locator: str


class SourcedSubmission(Contract):
    note: str
    cites: tuple[Cite, ...] = ()


class ViewedSubmission(Contract):
    note: str
    tags: tuple[str, ...] = ()


SCHEMAS: dict[str, type[SourcedSubmission] | type[ViewedSubmission]] = {
    SOURCED: SourcedSubmission,
    VIEWED: ViewedSubmission,
}


def _validate(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator the fake `submit` hands `Execution.submit_step` (its last step is the
    one under validation)."""
    step = attempt.steps[-1]
    try:
        submission = SCHEMAS[step.step_id].model_validate_json(store.payload(step.payload_sha256))
    except ValidationError:
        return StepValidation(issues=("Fake validator: malformed submission",))
    if submission.note == INVALID_MARK:
        return StepValidation(issues=(VALIDATOR_ISSUE,))
    output = {
        "step": step.step_id,
        "note": submission.note,
        "inputs": [i.input_id for i in step.inputs],
    }
    return StepValidation(output=json.dumps(output, sort_keys=True))


def _candidate(snapshot: ExecutionSnapshot, attempt: Attempt) -> Module:
    run = snapshot.run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=MODULE,
        inputs=attempt.inputs,
        attempt=attempt.number,
    )


def _same(candidate: Module) -> Callable[[Module], tuple[str, ...]]:
    return lambda supplied: () if supplied == candidate else ("Candidate differs",)


def _submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal one step (null resolution through SCHEMAS, the rule issues appended as the product
    `_with_rules` appends them) and settle the module after its last valid step."""
    normal, resolved = normalise(SCHEMAS[step_id], payload)
    validate: Callable[[PreparedPack, Attempt], StepValidation] = partial(_validate, store)
    if rules is not None and rules(normal):
        validate = _with_rules(validate, rules, normal)
    attempt = store.submit_step(ticket_id, MODULE, STEP_IDS, step_id, normal, validate)
    if (
        attempt.status == "pending"
        and len(attempt.steps) == len(STEP_IDS)
        and all(s.status == "valid" for s in attempt.steps)
    ):
        candidate = _candidate(store.read(), attempt)
        attempt = store.finish(
            ticket_id, candidate.model_dump_json(), _same(candidate), qualification=QUALIFICATION
        )
    return Submitted(attempt, normal, resolved, (), (), None)


def _probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Rerun every step's validator on the frozen view and re-settle back to the head."""
    if len(attempt.steps) != len(STEP_IDS) or any(s.status != "valid" for s in attempt.steps):
        raise WorkflowError("identity_mismatch")
    frozen = _FrozenExecution(store, snapshot)
    pack = store.pack(snapshot)
    for index, step in enumerate(attempt.steps):
        pending = step.model_copy(update={"status": "pending", "output_sha256": None, "issues": ()})
        view = attempt.model_copy(update={"steps": (*attempt.steps[:index], pending)})
        outcome = _validate(frozen, pack, view)
        if (
            outcome.issues
            or outcome.output is None
            or not outcome.retained_as(step)
            or store.step_output(step.output_sha256 or "") != outcome.output
        ):
            raise WorkflowError("identity_mismatch")
    candidate = _candidate(snapshot, attempt)
    finished, result = settle(
        snapshot,
        attempt,
        candidate.model_dump_json(),
        _same(candidate),
        pack=pack,
        load=store.head_module,
    )
    head = next(h for h in snapshot.heads if h.module_id == MODULE)
    if finished != attempt or result != store.head_module(head):
        raise WorkflowError("identity_mismatch")


def _view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """A deterministic view over the bound inputs and the steps already retained."""
    body = json.dumps(
        {
            "module_id": attempt.module_id,
            "attempt": attempt.number,
            "inputs": [[i.input_id, i.sha256] for i in attempt.inputs],
            "steps": [s.step_id for s in attempt.steps],
        },
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest(), body


def _precheck(store: Execution, binding: Any, stored: str) -> tuple[str, ...]:
    try:
        document = json.loads(stored)
    except ValueError:
        return ()
    return (GATE_ISSUE,) if isinstance(document, dict) and document.get("note") == GATE_MARK else ()


def _rules(text: str, seen: Seen) -> tuple[str, ...]:
    return unread_citation_issues(text, seen)


def _fake_core() -> ModuleType:
    core = ModuleType("g1x_fake_core")
    core.__dict__.update(
        MODULE_ID=MODULE,
        QUALIFICATION=QUALIFICATION,
        STEP_IDS=STEP_IDS,
        SCHEMAS=SCHEMAS,
        RULES=_rules,
        submit=_submit,
        probe=_probe,
        view=_view,
        precheck=_precheck,
        ENTRY_VALIDATOR=_validate,
    )
    return core


def _fake_spec() -> Any:
    sourced = owner.StepSpec(
        step_id=SOURCED,
        schema=SourcedSubmission,
        sources=True,
        extract=False,
        upstream_grant=None,
        inputs="module_context",
        rules="journaled",
    )
    viewed = owner.StepSpec(
        step_id=VIEWED,
        schema=ViewedSubmission,
        sources=False,
        extract=False,
        upstream_grant=None,
        inputs="module_context",
        rules="none",
    )
    return owner.OwnerSpec(
        module_id=MODULE,
        steps=(sourced, viewed),
        entry="owner_core",
        kind="analytical",
        publish=None,
    )


class _FakeSession:
    """Test-only stand-in for the H1 host scope of the fake module's sourced step: `read_pages`
    of one page is ok and recorded as read, every other tool is refused. Deterministic, so the
    verifier's replay through it reproduces every receipt but its call id. Any other module's
    step opens the real `SourceSession`."""

    def __init__(self, binding: dict[str, Any]) -> None:
        self._binding = binding
        self._calls: list[dict[str, Any]] = []
        self._read: list[tuple[str, str]] = []

    @classmethod
    def from_execution(cls, store: Execution, ticket_id: str, step_id: str) -> Any:
        snapshot = store.read()
        attempt = next(a for a in snapshot.attempts if a.ticket_id == ticket_id)
        if attempt.module_id != MODULE:
            return SourceSession.from_execution(store, ticket_id, step_id)
        return cls(owner._owner_binding(snapshot, attempt, step_id).model_dump(mode="json"))

    def _evidence(self) -> dict[str, Any]:
        evidence: dict[str, Any] = SourceEvidence(read=tuple(self._read)).model_dump(mode="json")
        return evidence

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        ok = (
            tool_name == "read_pages"
            and set(arguments) == {"source_id", "first_page", "last_page"}
            and arguments["first_page"] == arguments["last_page"]
        )
        page = (str(arguments.get("source_id")), f"page:{arguments.get('first_page')}")
        if ok and page not in self._read:
            self._read.append(page)
        receipt = {
            "schema_version": "tool-receipt/1",
            "call_id": str(uuid4()),
            "sequence": len(self._calls) + 1,
            "binding": self._binding,
            "tool": tool_name,
            "arguments": arguments,
            "status": "ok" if ok else "refused",
            "body": f"{page[0]} {page[1]}" if ok else None,
            "error_code": None if ok else "not_permitted",
            "source_evidence": self._evidence(),
        }
        self._calls.append(receipt)
        detached: dict[str, Any] = json.loads(json.dumps(receipt))
        return detached

    def bind_submission(self, payload: str) -> dict[str, Any]:
        return {
            "schema_version": "submission-binding/1",
            "binding": self._binding,
            "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "successful_call_ids": [c["call_id"] for c in self._calls if c["status"] == "ok"],
            "call_ids": [c["call_id"] for c in self._calls],
            "source_evidence": self._evidence(),
        }


@pytest.fixture
def g1x(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """Register the fake core exactly where a module task registers a real one."""
    core = _fake_core()
    spec = _fake_spec()
    monkeypatch.setattr(owner, "OWNER_SPECS", MappingProxyType({**owner.OWNER_SPECS, MODULE: spec}))
    monkeypatch.setattr(owner, "SUPPORTED_ANALYTICAL", owner.SUPPORTED_ANALYTICAL | {MODULE})
    monkeypatch.setitem(owner._CORES, MODULE, core)
    monkeypatch.setitem(owner._QUALIFICATION, MODULE, QUALIFICATION)
    monkeypatch.setitem(owner._PROBES, MODULE, _probe)
    monkeypatch.setitem(owner._VIEWS, SOURCED, _view)
    monkeypatch.setitem(owner._VIEWS, VIEWED, _view)
    monkeypatch.setitem(owner._PRECHECKS, MODULE, _precheck)
    monkeypatch.setitem(owner._ENTRY_VALIDATORS, MODULE, _validate)
    monkeypatch.setattr(owner, "SourceSession", _FakeSession)
    yield SimpleNamespace(core=core, spec=spec, monkeypatch=monkeypatch)


# --- run helpers ------------------------------------------------------------------------------


def _pack() -> PreparedPack:
    """The S1 positive pack with the fake module the only requested module (plan CP-0, CP-3D)."""
    pack = runs.make_pack("positive")
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = [MODULE]
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)


def _cp0_review(pack: PreparedPack) -> str:
    """The S1 CP-0 literal (READY, "Run <module>") with its CP-1A consumer row standing for the
    fake module, the only live consumer of this plan."""
    review = json.loads(runs.literal("positive", "readiness_review", pack))
    review["pack_sha256"] = pack.content_hash()
    consumer = next(c for c in review["consumers"] if c["module_id"] == "CP-1A")
    review["consumers"] = [{**consumer, "module_id": MODULE}]
    return json.dumps(review)


def _create(root: Path) -> Any:
    return owner.OwnerWorkflow.create(root / "store", _pack(), specs=owner.OWNER_SPECS)


def _start(root: Path) -> Any:
    """CP-0 valid (real session and evidence rules) and the fake module begun at its first
    step."""
    workflow = _create(root)
    review = _cp0_review(_pack())
    runs.read_cited(workflow, review)
    assert workflow.submit_review(review)["status"] == "valid"
    return workflow


def _sourced(note: str = "fine") -> str:
    return json.dumps({"note": note, "cites": [{"source_id": "financial", "locator": "page:1"}]})


def _viewed(note: str = "fine") -> str:
    return json.dumps({"note": note, "tags": None})


def _read_page(workflow: Any) -> None:
    call = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert call["status"] == "ok"


def _drive(workflow: Any) -> None:
    """From the sourced step to the settled module: read, read the cited page, submit; then the
    viewed step's read and submit."""
    workflow.read_inputs()
    _read_page(workflow)
    assert workflow.submit_review(_sourced())["status"] == "valid"
    workflow.read_inputs()
    assert workflow.submit_review(_viewed())["status"] == "valid"


def _fake_attempts(root: Path) -> list[Attempt]:
    return [a for a in Execution(root / "store").read().attempts if a.module_id == MODULE]


def _verdict(root: Path, receipt: Any) -> str:
    try:
        owner.verify_owner_run_receipt(Execution(root / "store"), receipt)
    except WorkflowError as error:
        return str(error.code)
    return "accepted"


def _reseal(root: Path, receipt: Any) -> None:
    store = Execution(root / "store")
    seal = store.directory / owner.AUDIT / "receipt.sha256"
    seal.unlink()
    owner._put(seal, receipt.content_hash().encode())


def _swap(root: Path, kind: str, old: Any, new: Any | None) -> None:
    store = Execution(root / "store")
    (store.directory / owner.AUDIT / kind / old.content_hash()).unlink()
    if new is not None:
        owner._retain(store, kind, new)


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _sealed(root: Path) -> Any:
    workflow = _start(root)
    _drive(workflow)
    return workflow.write_receipt(root / "receipt.json")


# --- §1/§2 entry and registration ---------------------------------------------------------------


def test_fake_module_is_owner_only_and_plans_after_cp0() -> None:
    with pytest.raises(ValueError, match="has no live step contract"):
        step_chain(MODULE)
    assert plan([MODULE]) == ("CP-0", MODULE)


def test_owner_only_spec_must_be_served_by_its_core(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """§1: an owner-only module has `entry == "owner_core"` exactly and its registered core's
    `STEP_IDS`; a live-contract module never takes the owner-core entry. Refusals write nothing."""
    spec = g1x.spec
    sourced, viewed = spec.steps
    variants: dict[str, tuple[str, Any, Callable[[pytest.MonkeyPatch], None]]] = {
        "live entry": (MODULE, replace(spec, entry="model_payload"), lambda m: None),
        "no registered core": (MODULE, spec, lambda m: m.delitem(owner._CORES, MODULE)),
        "steps differ from STEP_IDS": (MODULE, replace(spec, steps=(sourced,)), lambda m: None),
        "module_context without a view": (MODULE, spec, lambda m: m.delitem(owner._VIEWS, VIEWED)),
        "journaled without sources": (
            MODULE,
            replace(spec, steps=(replace(sourced, sources=False), viewed)),
            lambda m: None,
        ),
        "extraction offered": (
            MODULE,
            replace(spec, steps=(replace(sourced, extract=True), viewed)),
            lambda m: None,
        ),
        "financial precheck rules": (
            MODULE,
            replace(spec, steps=(sourced, replace(viewed, rules="precheck"))),
            lambda m: None,
        ),
        "live-contract module with the owner-core entry": (
            "CP-1A",
            replace(owner.OWNER_SPECS["CP-1A"], entry="owner_core"),
            lambda m: None,
        ),
    }
    for label, (module_id, variant, patch) in variants.items():
        root = tmp_path / label.replace(" ", "-")
        root.mkdir()
        pack = _pack()
        if module_id != MODULE:
            document = json.loads(pack.run.model_dump_json())
            document["requested_modules"] = [module_id]
            pack = PreparedPack(
                run=Run.model_validate_json(json.dumps(document)), sources=pack.sources
            )
        with pytest.MonkeyPatch.context() as m:
            specs = MappingProxyType({**owner.OWNER_SPECS, module_id: variant})
            m.setattr(owner, "OWNER_SPECS", specs)
            patch(m)
            with pytest.raises(WorkflowError) as caught:
                owner.OwnerWorkflow.create(root / "store", pack, specs=specs)
        assert caught.value.code == "not_permitted", label
        assert list(root.iterdir()) == [], label


def test_owner_core_submit_walks_step_ids_and_seals(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """§2: the owner-core entry journals through `core.submit`, G1 walks `core.STEP_IDS`, the
    module settles with the core's qualification and the sealed receipt verifies read-only."""
    workflow = _start(tmp_path)
    assert (workflow._binding.module_id, workflow._binding.step_id) == (MODULE, SOURCED)
    workflow.read_inputs()
    _read_page(workflow)
    first = workflow.submit_review(_sourced())
    assert (first["status"], first["issues"], first["next_step"]) == ("valid", [], VIEWED)
    (attempt,) = _fake_attempts(tmp_path)
    assert attempt.status == "pending"
    assert [(s.step_id, s.status) for s in attempt.steps] == [(SOURCED, "valid")]
    # the session-less step offers no pack tool
    refused = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert (refused["status"], refused["error_code"]) == ("refused", "not_permitted")
    body = json.loads(workflow.read_inputs()["body"])
    assert body["steps"] == [SOURCED]
    second = workflow.submit_review(_viewed())
    assert (second["status"], second["next_step"]) == ("valid", None)
    (attempt,) = _fake_attempts(tmp_path)
    assert attempt.status == "finished" and not attempt.issues
    assert tuple(s.step_id for s in attempt.steps) == STEP_IDS
    store = Execution(tmp_path / "store")
    head = next(h for h in store.read().heads if h.module_id == MODULE)
    assert head.status in ("accepted", "restricted")
    assert head.qualification == QUALIFICATION
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [s.disposition for s in receipt.submissions] == ["valid", "valid", "valid"]
    before = _tree(tmp_path / "store")
    owner.verify_owner_run_receipt(store, receipt)
    assert _tree(tmp_path / "store") == before


def test_owner_core_result_must_match_what_g1_retains(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """§2: G1's identity check (payload, nulls_resolved, prefilled, prefilled_kinds) holds for the
    `Submitted` an owner core returns."""

    def dishonest(*args: Any) -> Submitted:
        return replace(_submit(*args), payload="{}")

    g1x.monkeypatch.setattr(g1x.core, "submit", dishonest)
    workflow = _start(tmp_path)
    workflow.read_inputs()
    _read_page(workflow)
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(_sourced())
    assert caught.value.code == "identity_mismatch"


def test_owner_historical_follows_core_step_ids(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """§2: `_owner_historical` (used by `_activate` and the verifier) takes the core's `STEP_IDS`
    as the sequence: only the next step in that order binds."""
    _start(tmp_path)
    assert owner._sequence(MODULE) == STEP_IDS
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    (attempt,) = _fake_attempts(tmp_path)
    owner._owner_historical(store, owner._owner_binding(snapshot, attempt, SOURCED))
    with pytest.raises(WorkflowError) as caught:
        owner._owner_historical(store, owner._owner_binding(snapshot, attempt, VIEWED))
    assert caught.value.code == "identity_mismatch"


def test_fill_normalises_through_core_schemas(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """§2: a step outside `live.submission.STEPS` is normalised through `core.SCHEMAS`: the null
    standing for an omitted default resolves to it and its path is recorded."""
    workflow = _start(tmp_path)
    store = Execution(tmp_path / "store")
    snapshot = store.read()
    (attempt,) = _fake_attempts(tmp_path)
    binding = owner._owner_binding(snapshot, attempt, VIEWED)
    stored, resolved, paths, kinds = owner._fill(store, binding, _viewed())
    assert json.loads(stored) == {"note": "fine", "tags": []}
    assert (resolved, paths, kinds) == (("tags",), (), ())
    _drive(workflow)
    record = workflow._submissions[-1]
    assert record.nulls_resolved == ("tags",)
    raw = (tmp_path / "store" / owner.AUDIT / "payloads" / record.stored_payload_sha256).read_text()
    assert json.loads(raw) == {"note": "fine", "tags": []}


# --- §2 RULES routing ---------------------------------------------------------------------------


def test_rules_route_to_the_core(g1x: SimpleNamespace) -> None:
    """§2: a journaled owner-only step is judged by `core.RULES(text, seen)` over the session's
    `Seen`, not by `ToolRules`."""
    assert owner._journaled_issues(MODULE, SOURCED, _sourced(), SourceEvidence()) == (UNREAD,)
    read = SourceEvidence(read=(("financial", "page:1"),))
    assert owner._journaled_issues(MODULE, SOURCED, _sourced(), read) == ()


def test_rules_at_submit_journal_an_invalid_step_and_the_verifier_replays_it(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    """§2 at submit: an unread cited page makes the step invalid through `RULES`; attempt 0 is
    consumed and re-begun as attempt 1. In the verifier: the invalid step's issues are rebuilt
    from the validator replay plus the recomputed `RULES`, and the receipt verifies."""
    workflow = _start(tmp_path)
    workflow.read_inputs()
    outcome = workflow.submit_review(_sourced())
    assert (outcome["status"], outcome["issues"], outcome["next_step"]) == (
        "invalid",
        [UNREAD],
        SOURCED,
    )
    rejected, repair = _fake_attempts(tmp_path)
    assert (rejected.number, rejected.status, rejected.issues) == (0, "finished", (UNREAD,))
    assert rejected.steps[-1].issues == (UNREAD,)
    assert (repair.number, repair.status, repair.repair_of) == (1, "pending", rejected.ticket_id)
    _drive(workflow)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert [s.disposition for s in receipt.submissions] == ["valid", "invalid", "valid", "valid"]
    assert _verdict(tmp_path, receipt) == "accepted"


def test_verifier_recomputes_rules_for_a_valid_step(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """§2 in the verifier: a core that ignored the rules journals a valid step `RULES` refuses;
    the verifier's recomputation catches it and no receipt is sealed."""

    def ignores_rules(*args: Any) -> Submitted:
        return _submit(*args[:4], None)

    g1x.monkeypatch.setattr(g1x.core, "submit", ignores_rules)
    workflow = _start(tmp_path)
    workflow.read_inputs()
    assert workflow.submit_review(_sourced())["status"] == "valid"  # the page was never read
    workflow.read_inputs()
    assert workflow.submit_review(_viewed())["status"] == "valid"
    with pytest.raises(WorkflowError) as caught:
        workflow.write_receipt(tmp_path / "receipt.json")
    assert caught.value.code == "identity_mismatch"
    assert not (tmp_path / "receipt.json").exists()


# --- §3 inputs ----------------------------------------------------------------------------------


def test_module_context_read_required_with_and_without_a_session(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    """§3: `read_inputs` precedes `submit_review` for every step whose inputs are not "none": the
    sourced step (with a session) and the viewed one (without). A refused submit records
    nothing."""
    workflow = _start(tmp_path)
    _read_page(workflow)
    for payload in (_sourced(), _viewed()):
        recorded = len(workflow._submissions)
        before = Execution(tmp_path / "store").read()
        with pytest.raises(WorkflowError) as caught:
            workflow.submit_review(payload)
        assert caught.value.code == "not_permitted"
        assert len(workflow._submissions) == recorded
        assert Execution(tmp_path / "store").read() == before
        workflow.read_inputs()
        assert workflow.submit_review(payload)["status"] == "valid"


def test_verifier_requires_the_read_of_a_sourced_view_step(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    """§3 in the verifier: a receipt whose sourced step's read is removed (audit and seal made
    consistent with it) refuses."""
    receipt = _sealed(tmp_path)
    read = next(r for r in receipt.input_reads if r.binding.step_id == SOURCED)
    forged = receipt.model_copy(
        update={"input_reads": tuple(r for r in receipt.input_reads if r != read)}
    )
    _swap(tmp_path, "input-reads", read, None)
    _reseal(tmp_path, forged)
    assert _verdict(tmp_path, forged) == "identity_mismatch"


# --- §4 precheck gate ---------------------------------------------------------------------------


def _refused_then_sealed(root: Path) -> Any:
    """A gate refusal on the sourced step (before any rule: the cited page is unread too), then a
    corrected resubmission on the same ticket, then the rest of the run, sealed."""
    workflow = _start(root)
    workflow.read_inputs()
    store = Execution(root / "store")
    before = store.read()
    (attempt,) = _fake_attempts(root)
    outcome = workflow.submit_review(_sourced(GATE_MARK))
    assert (outcome["status"], outcome["issues"], outcome["next_step"]) == (
        "refused",
        [GATE_ISSUE],
        SOURCED,
    )
    after = store.read()
    assert after == before and outcome["snapshot_sha256"] == before.content_hash()
    assert _fake_attempts(root) == [attempt]  # no journal step, no attempt consumed
    assert not any(h.module_id == MODULE for h in after.heads)
    record = workflow._submissions[-1]
    assert (record.disposition, record.issues, record.step_sha256) == (
        "refused",
        (GATE_ISSUE,),
        None,
    )
    _read_page(workflow)
    assert workflow.submit_review(_sourced())["status"] == "valid"
    (same,) = _fake_attempts(root)
    assert (same.ticket_id, same.number) == (attempt.ticket_id, 0)
    workflow.read_inputs()
    assert workflow.submit_review(_viewed())["status"] == "valid"
    return workflow.write_receipt(root / "receipt.json")


def test_precheck_refusal_consumes_no_attempt_then_corrected_resubmission(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    receipt = _refused_then_sealed(tmp_path)
    assert [s.disposition for s in receipt.submissions] == ["valid", "refused", "valid", "valid"]
    assert _verdict(tmp_path, receipt) == "accepted"


def test_verifier_recomputes_the_gate(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """§4 in the verifier: a refused record must reproduce exactly its recomputed issues, and a
    journaled step must recompute none."""
    receipt = _refused_then_sealed(tmp_path / "run")

    def fork(name: str) -> Path:
        shutil.copytree(tmp_path / "run", tmp_path / name)
        return tmp_path / name

    # a forged refused record: its issues rewritten, audit and seal consistent with the forgery
    root = fork("forged-issues")
    old = next(s for s in receipt.submissions if s.disposition == "refused")
    new = old.model_copy(update={"issues": ("Gate: an invented refusal",)})
    forged = receipt.model_copy(
        update={"submissions": tuple(new if s == old else s for s in receipt.submissions)}
    )
    _swap(root, "submissions", old, new)
    _reseal(root, forged)
    assert _verdict(root, forged) == "identity_mismatch"
    # the gate is recomputed, not trusted: without it the refused record has no cause ...
    root = fork("no-gate")
    with pytest.MonkeyPatch.context() as m:
        m.delitem(owner._PRECHECKS, MODULE)
        assert _verdict(root, receipt) == "identity_mismatch"
    # ... and a gate that refuses everything finds issues on the journaled steps
    root = fork("gate-refuses-all")
    with pytest.MonkeyPatch.context() as m:
        m.setitem(owner._PRECHECKS, MODULE, lambda store, binding, stored: (GATE_ISSUE,))
        assert _verdict(root, receipt) == "identity_mismatch"
    assert _verdict(tmp_path / "run", receipt) == "accepted"


# --- R4-4 verifier exception mapping ----------------------------------------------------------


def test_verifier_programming_errors_propagate(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """R4-4: a programming error inside the verifier is never relabelled as tamper."""
    receipt = _sealed(tmp_path)
    store = Execution(tmp_path / "store")

    def raising(error: BaseException) -> Callable[..., Any]:
        def call(*args: Any) -> Any:
            raise error

        return call

    cases: list[tuple[str, Any, type[BaseException]]] = [
        ("_PROBES", MODULE, TypeError),
        ("_VIEWS", VIEWED, KeyError),
        ("_PRECHECKS", MODULE, StopIteration),
    ]
    for registry, key, error in cases:
        with pytest.MonkeyPatch.context() as m:
            m.setitem(getattr(owner, registry), key, raising(error("a programming error")))
            with pytest.raises(error):
                owner.verify_owner_run_receipt(store, receipt)
    owner.verify_owner_run_receipt(store, receipt)


def test_verifier_tamper_causes_map_to_identity_mismatch(
    g1x: SimpleNamespace, tmp_path: Path
) -> None:
    """R4-4: tamper causes refuse `identity_mismatch`, including those that used to surface as a
    raw lookup failure, now explicit checks."""
    receipt = _sealed(tmp_path / "run")

    def fork(name: str) -> Path:
        shutil.copytree(tmp_path / "run", tmp_path / name)
        return tmp_path / name

    # a deleted audit payload (OSError)
    root = fork("deleted-payload")
    digest = receipt.submissions[-1].binding.payload_sha256
    (root / "store" / owner.AUDIT / "payloads" / digest).unlink()
    assert _verdict(root, receipt) == "identity_mismatch"
    # a forged final snapshot whose module head has no attempt that settled it
    root = fork("head-without-attempt")
    store = Execution(root / "store")
    snapshot = store.read()
    store._write(
        snapshot.model_copy(
            update={
                "parent": snapshot.content_hash(),
                "attempts": tuple(a for a in snapshot.attempts if a.module_id != MODULE),
            }
        )
    )
    forged = receipt.model_copy(update={"snapshot_sha256": store.read().content_hash()})
    _reseal(root, forged)
    assert _verdict(root, forged) == "identity_mismatch"
    # a store whose run plans modules without a spec (CP-3, CP-5, CP-6, CP-MEMO), with a receipt
    # naming that plan (`create` refuses such a run; only a forged store holds one)
    pack = _pack()
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = ["CP-MEMO"]
    pack = PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)
    store = Execution.create(tmp_path / "unspecced" / "store", pack)
    snapshot = store.read()
    unspecced = owner.OwnerRunReceipt(
        run=snapshot.run,
        pack_sha256=snapshot.pack_sha256,
        snapshot_sha256=snapshot.content_hash(),
        participant="trusted-python",
        transport="python-api",
        plan=plan(snapshot.run.requested_modules),
        heads=(),
        model=None,
        begins=(),
        refusals=(),
        calls=(),
        input_reads=(),
        submissions=(),
        publications=(),
    )
    assert any(m not in owner.OWNER_SPECS for m in unspecced.plan)
    assert _verdict(tmp_path / "unspecced", unspecced) == "identity_mismatch"
