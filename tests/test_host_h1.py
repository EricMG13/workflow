"""H1 acceptance: the fixed host source mapping for owner-only and CP-3 sourced steps
(`docs/G1X-OWNER-CORE-PROTOCOL.md` §3 and §5; LEAD ruling Q6, `work/build/h1/q6-source.md`).

Expectations come from the leases, never from the code under test:
- rows (`docs/CP3-OWNER-LEASE.md:53-65`, `docs/CP3D-OWNER-LEASE.md:46,87`,
  `docs/CPDR-OWNER-LEASE.md:31`, `docs/CP1D-OWNER-LEASE.md:30` and
  `cases/cp1d-owner/manifest.json` "fixed H1 mapping"): CP-3 `relative_value` keeps the
  registry's scope; CP-3D `market_implied` reads market and financial only; CP-DR `research` the
  whole ready pack; CP-1D `earnings_quality` identity, financial and bridge as the pack holds them;
- an owner-only module's step order is its registered G1-X core's, never `step_chain`'s;
- the `*-submission` producer rule (Q6 (b)) and its memo per (snapshot hash, producer hash).

The owner cores of CP-3D and CP-DR register in their own Stage 2 tasks, so each session test
registers a test-only one-step core (`_fake_core`, the G1-X fake-core pattern of
`tests/test_owner_g1x.py`) exactly where a module task registers a real one. Unlike G1-X, no
session double is installed: every session here is the real `host.SourceSession`. The fake core
is not product code. The producer rule runs over real CP-1A heads settled through the public
`OwnerWorkflow` API on a plan of CP-0 and CP-1A (no CP-1 promotion), each well under a second.
"""

import hashlib
import importlib
import json
from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path
from types import MappingProxyType, ModuleType, SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from deploy_vii.contracts import Contract, Input, Module, Run, Source, Span
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
from deploy_vii.live.tools import unread_citation_issues
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import step_chain
from deploy_workflow import host
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.host import SourceSession
from deploy_workflow.tools.source import SourceError
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("s1a_runs")

ROOT = Path(__file__).resolve().parents[1]
CP3D_ORACLE = ROOT / "cases/cp3d-owner"
QUALIFICATION = Qualification(implementation="implemented")
UNREAD = "Cited page not read through read_pages: {} {}"


# --- the test-only fake owner core (one sourced, journaled step) --------------------------------


class Cite(Contract):
    source_id: str
    locator: str


class Note(Contract):
    note: str
    cites: tuple[Cite, ...] = ()


def _fake_core(module: str, step: str) -> ModuleType:
    """A one-step owner core for `module`: its step validates any `Note`, settles the module and
    rebuilds it in `probe`; `RULES` is the product cited-page rule (G1-X §2)."""
    steps = (step,)

    def validate(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
        retained = attempt.steps[-1]
        try:
            note = Note.model_validate_json(store.payload(retained.payload_sha256))
        except ValidationError:
            return StepValidation(issues=("Fake validator: malformed note",))
        return StepValidation(output=json.dumps({"module": module, "note": note.note}))

    def candidate(snapshot: ExecutionSnapshot, attempt: Attempt) -> Module:
        run = snapshot.run
        return Module(
            run_id=run.run_id,
            issuer_id=run.issuer_id,
            as_of=run.as_of,
            module_id=module,
            inputs=attempt.inputs,
            attempt=attempt.number,
        )

    def same(expected: Module) -> Callable[[Module], tuple[str, ...]]:
        return lambda supplied: () if supplied == expected else ("Candidate differs",)

    def submit(
        store: Execution,
        ticket_id: str,
        step_id: str,
        payload: str,
        rules: Callable[[str], tuple[str, ...]] | None,
    ) -> Submitted:
        normal, resolved = normalise(Note, payload)
        validator: Callable[[PreparedPack, Attempt], StepValidation] = partial(validate, store)
        if rules is not None and rules(normal):
            validator = _with_rules(validator, rules, normal)
        attempt = store.submit_step(ticket_id, module, steps, step_id, normal, validator)
        if attempt.status == "pending" and all(s.status == "valid" for s in attempt.steps):
            settled = candidate(store.read(), attempt)
            attempt = store.finish(
                ticket_id, settled.model_dump_json(), same(settled), qualification=QUALIFICATION
            )
        return Submitted(attempt, normal, resolved, (), (), None)

    def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        if len(attempt.steps) != 1 or attempt.steps[0].status != "valid":
            raise WorkflowError("identity_mismatch")
        retained = attempt.steps[0]
        pending = retained.model_copy(update={"status": "pending", "output_sha256": None})
        pack = store.pack(snapshot)
        outcome = validate(
            _FrozenExecution(store, snapshot),
            pack,
            attempt.model_copy(update={"steps": (pending,)}),
        )
        if (
            outcome.issues
            or not outcome.retained_as(retained)
            or store.step_output(retained.output_sha256 or "") != outcome.output
        ):
            raise WorkflowError("identity_mismatch")
        settled = candidate(snapshot, attempt)
        finished, result = settle(
            snapshot,
            attempt,
            settled.model_dump_json(),
            same(settled),
            pack=pack,
            load=store.head_module,
        )
        head = next(h for h in snapshot.heads if h.module_id == module)
        if finished != attempt or result != store.head_module(head):
            raise WorkflowError("identity_mismatch")

    core = ModuleType(f"h1_fake_core_{module}")
    core.__dict__.update(
        MODULE_ID=module,
        QUALIFICATION=QUALIFICATION,
        STEP_IDS=steps,
        SCHEMAS={step: Note},
        RULES=unread_citation_issues,
        submit=submit,
        probe=probe,
        ENTRY_VALIDATOR=validate,
    )
    return core


def _register(monkeypatch: pytest.MonkeyPatch, module: str, step: str) -> ModuleType:
    """Register the fake core exactly where a module task registers a real one; the session
    stays the real `SourceSession`."""
    core = _fake_core(module, step)
    spec = owner.OwnerSpec(
        module_id=module,
        steps=(
            owner.StepSpec(
                step_id=step,
                schema=Note,
                sources=True,
                extract=False,
                upstream_grant=None,
                inputs="none",
                rules="journaled",
            ),
        ),
        entry="owner_core",
        kind="analytical",
        publish=None,
    )
    monkeypatch.setattr(owner, "OWNER_SPECS", MappingProxyType({**owner.OWNER_SPECS, module: spec}))
    monkeypatch.setattr(owner, "SUPPORTED_ANALYTICAL", owner.SUPPORTED_ANALYTICAL | {module})
    monkeypatch.setitem(owner._CORES, module, core)
    monkeypatch.setitem(owner._QUALIFICATION, module, QUALIFICATION)
    monkeypatch.setitem(owner._PROBES, module, core.probe)
    monkeypatch.setitem(owner._ENTRY_VALIDATORS, module, core.ENTRY_VALIDATOR)
    return core


@pytest.fixture(autouse=True)
def _fresh_memo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with an empty producer memo, so a hit is always this test's own."""
    monkeypatch.setattr(host, "_SUBMISSION_VERIFIED", {}, raising=False)


# --- packs and runs ---------------------------------------------------------------------------


def _requested(pack: PreparedPack, *requested: str) -> PreparedPack:
    document = json.loads(pack.run.model_dump_json())
    document["requested_modules"] = list(requested)
    return PreparedPack(run=Run.model_validate_json(json.dumps(document)), sources=pack.sources)


def _cp3d_pack() -> PreparedPack:
    """The CP-3D positive run's pack (`cases/cp3d-owner/manifest.json`): identity and financial
    of the hash-checked S1 pack, the pinned market sheet, the oracle's run."""
    manifest = json.loads((CP3D_ORACLE / "manifest.json").read_text())
    case = next(c for c in manifest["cases"] if c["case_id"] == "positive")
    held = {s.source_id: s for s in runs.make_pack("positive").sources}
    market = manifest["market_source_pin"]
    joined = "\f".join(p["text"] for p in market["pages"]).encode()
    assert hashlib.sha256(joined).hexdigest() == market["source_sha256"]
    sources = []
    for item in case["pack_sources"]:
        if item["source_id"] == "market":
            source = Source(
                source_id="market",
                name=item["name"],
                status="ready",
                sha256=market["source_sha256"],
                media_type="text/plain",
                spans=tuple(Span(**page) for page in market["pages"]),
                extraction_status="complete",
            )
        else:
            source = held[item["source_id"]]
        assert (source.source_id, source.name, source.sha256) == (
            item["source_id"],
            item["name"],
            item["sha256"],
        )
        sources.append(source)
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(case["run"])), sources=tuple(sources)
    )


def _cp3d_review(pack: PreparedPack) -> str:
    """The CP-3D oracle's CP-0 literal (`submissions.json#readiness_review.positive`)."""
    document = json.loads((CP3D_ORACLE / "submissions.json").read_text())
    text = json.dumps(document["readiness_review"]["positive"], ensure_ascii=False)
    return text.replace(runs.PACK_PLACEHOLDER, pack.content_hash())


def _s1_review(pack: PreparedPack, module: str) -> str:
    """The S1 CP-0 literal with its CP-1A consumer row standing for `module`, the only live
    consumer of the plan (the G1-X `_cp0_review` pattern)."""
    review = json.loads(runs.literal("positive", "readiness_review", pack))
    consumer = next(c for c in review["consumers"] if c["module_id"] == "CP-1A")
    review["consumers"] = [{**consumer, "module_id": module}]
    return json.dumps(review)


def _begun(root: Path, pack: PreparedPack, review: str) -> Any:
    """CP-0 settled through the real session and the plan's next module begun."""
    workflow = owner.OwnerWorkflow.create(root / "store", pack, specs=owner.OWNER_SPECS)
    runs.read_cited(workflow, review)
    assert workflow.submit_review(review)["status"] == "valid"
    return workflow


def _read(workflow: Any, source_id: str, page: int) -> dict[str, Any]:
    call: dict[str, Any] = workflow.invoke(
        "read_pages", {"source_id": source_id, "first_page": page, "last_page": page}
    )
    return call


def _note(*cites: tuple[str, str]) -> str:
    return json.dumps(
        {"note": "fine", "cites": [{"source_id": s, "locator": loc} for s, loc in cites]}
    )


def _sealed_verdict(workflow: Any, root: Path) -> str:
    receipt = workflow.write_receipt(root / "receipt.json")
    try:
        owner.verify_owner_run_receipt(Execution(root / "store"), receipt)
    except WorkflowError as error:
        return str(error.code)
    return "accepted"


def _pending(root: Path) -> Attempt:
    pending = [a for a in Execution(root / "store").read().attempts if a.status == "pending"]
    assert len(pending) == 1
    return pending[0]


@pytest.fixture
def cp3d(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[SimpleNamespace]:
    """CP-0 settled on the CP-3D pack and CP-3D begun at `market_implied` (fake core)."""
    core = _register(monkeypatch, "CP-3D", "market_implied")
    pack = _cp3d_pack()
    workflow = _begun(tmp_path, pack, _cp3d_review(pack))
    yield SimpleNamespace(workflow=workflow, core=core, pack=pack, root=tmp_path)


# --- 1. the fixed mapping -----------------------------------------------------------------------


def test_fixed_rows_name_each_leased_step() -> None:
    """Item 1: one row per sourced step; the CP-0, CP-1, CP-1A and CP-4 rows are unchanged."""
    assert host._SOURCE_STEPS == {
        "CP-0": ("source_readiness",),
        "CP-1": ("source_context", "financials"),
        "CP-1A": ("business_context",),
        "CP-4": ("legal_covenants",),
        "CP-3": ("relative_value",),
        "CP-3D": ("market_implied",),
        "CP-DR": ("research",),
        "CP-1D": ("earnings_quality",),
    }
    # CP-3 is a live-contract module: its scope stays the registry's (CP-3 lease :65); the
    # three others are owner-only and take the fixed host scope.
    assert "relative_value" in step_chain("CP-3").pack_sources
    for module in ("CP-3D", "CP-DR", "CP-1D"):
        with pytest.raises(ValueError, match="has no live step contract"):
            step_chain(module)
    assert set(host._OWNER_SCOPES) == {
        ("CP-3D", "market_implied"),
        ("CP-DR", "research"),
        ("CP-1D", "earnings_quality"),
    }


def _source(source_id: str, *, ready: bool = True) -> Source:
    """A pack source for the scope functions only (no run reads it)."""
    if not ready:
        return Source(source_id=source_id, name=source_id, status="missing", limitation="absent")
    return Source(
        source_id=source_id,
        name=source_id,
        status="ready",
        sha256="0" * 64,
        spans=(Span(locator="page:1", text=source_id),),
    )


def _scope(module: str, step: str, *source_ids: str, missing: tuple[str, ...] = ()) -> Any:
    pack = runs.make_pack("positive")
    sources = (
        *(_source(s) for s in source_ids),
        *(_source(s, ready=False) for s in missing),
    )
    return host._OWNER_SCOPES[(module, step)](PreparedPack(run=pack.run, sources=tuple(sources)))


def test_owner_scopes_are_the_leased_sources_in_pack_order() -> None:
    every = ("identity", "business", "market", "financial", "bridge", "peers")
    # CP-3D: market and financial only, never identity (CP-3D lease :46).
    assert _scope("CP-3D", "market_implied", *every) == ("market", "financial")
    assert _scope("CP-3D", "market_implied", "identity", "financial") == ("financial",)
    # CP-1D: identity, financial and bridge as the pack holds them; the statements_only pack
    # holds no bridge (CP-1D lease :30; manifest "fixed H1 mapping").
    assert _scope("CP-1D", "earnings_quality", *every) == ("identity", "financial", "bridge")
    assert _scope("CP-1D", "earnings_quality", "identity", "financial") == (
        "identity",
        "financial",
    )
    # CP-DR: the whole ready pack (CP-DR lease :31, D-B); a source that is not ready is not in it.
    assert _scope("CP-DR", "research", *every, missing=("late",)) == every
    # A named source the pack holds but cannot read stays named (the session then answers
    # `unavailable`, never its bytes).
    assert _scope("CP-3D", "market_implied", "financial", missing=("market",)) == (
        "financial",
        "market",
    )


# --- 2. real sessions over the fixed scope ------------------------------------------------------


def test_cp3d_session_opens_over_market_and_financial(cp3d: SimpleNamespace) -> None:
    workflow = cp3d.workflow
    assert type(workflow._session) is SourceSession
    assert workflow._binding.module_id == "CP-3D"
    assert _read(workflow, "market", 1)["status"] == "ok"
    assert _read(workflow, "financial", 5)["status"] == "ok"
    identity = _read(workflow, "identity", 1)
    assert (identity["status"], identity["error_code"]) == ("refused", "not_permitted")
    extract = workflow.invoke(
        "extract_statements", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert (extract["status"], extract["error_code"]) == ("refused", "not_permitted")
    search = workflow.invoke("search_pack", {"query": "Northbridge", "source_id": None})
    assert search["status"] == "ok"
    surfaced = {source for source, _ in search["source_evidence"]["surfaced"]}
    assert surfaced and surfaced <= {"market", "financial"}
    outcome = workflow.submit_review(_note(("market", "page:1"), ("financial", "page:5")))
    assert outcome["status"] == "valid"
    assert _sealed_verdict(workflow, cp3d.root) == "accepted"


def test_unread_cited_page_refuses_and_the_repair_attempt_reopens(cp3d: SimpleNamespace) -> None:
    """A cited page the session never returned is a journaled issue through the core's RULES
    over the real session's evidence; attempt 1 reopens a real session over the same scope."""
    workflow = cp3d.workflow
    assert _read(workflow, "market", 1)["status"] == "ok"
    outcome = workflow.submit_review(_note(("market", "page:1"), ("market", "page:2")))
    assert outcome["status"] == "invalid"
    assert outcome["issues"] == [UNREAD.format("market", "page:2")]
    repair = _pending(cp3d.root)
    assert (repair.module_id, repair.number) == ("CP-3D", 1)
    assert type(workflow._session) is SourceSession
    assert workflow._binding.ticket_id == repair.ticket_id
    assert _read(workflow, "market", 2)["status"] == "ok"
    assert _read(workflow, "identity", 1)["error_code"] == "not_permitted"
    assert workflow.submit_review(_note(("market", "page:2")))["status"] == "valid"
    assert _sealed_verdict(workflow, cp3d.root) == "accepted"


def test_cpdr_session_reads_the_whole_ready_pack(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _register(monkeypatch, "CP-DR", "research")
    pack = _requested(runs.make_pack("positive"), "CP-DR")
    workflow = _begun(tmp_path, pack, _s1_review(pack, "CP-DR"))
    assert type(workflow._session) is SourceSession
    assert workflow._binding.module_id == "CP-DR"
    for source in ("identity", "financial", "business"):
        assert _read(workflow, source, 1)["status"] == "ok", source
    outcome = workflow.submit_review(_note(("business", "page:1")))
    assert outcome["status"] == "valid"
    assert _sealed_verdict(workflow, tmp_path) == "accepted"


class _NoCapability:
    """Stands in for `SourceTools`: constructing it fails the test (a capability opened)."""

    def __init__(self, *_: Any, **__: Any) -> None:
        raise AssertionError("a source capability opened")


def _refusal(root: Path, step_id: str) -> str:
    try:
        SourceSession.from_execution(Execution(root / "store"), _pending(root).ticket_id, step_id)
    except SourceError as error:
        return str(error.code)
    return "opened"


def test_unregistered_owner_module_refuses_before_any_capability(
    cp3d: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Item 2: no core registered -> `not_permitted`, and no `SourceTools` is ever built."""
    assert _refusal(cp3d.root, "market_implied") == "opened"
    monkeypatch.setattr(host, "SourceTools", _NoCapability)
    monkeypatch.delitem(owner._CORES, "CP-3D")
    assert _refusal(cp3d.root, "market_implied") == "not_permitted"


def test_owner_step_outside_its_row_or_order_refuses(
    cp3d: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The row and the core's step order both bind: a step of another row, a step the core does
    not have first, or a core without a well-formed `STEP_IDS` is `not_permitted`."""
    monkeypatch.setattr(host, "SourceTools", _NoCapability)
    for step_id in ("research", "relative_value", "g1x_sourced"):
        assert _refusal(cp3d.root, step_id) == "not_permitted", step_id
    malformed = (
        ("prior_step", "market_implied"),
        ["market_implied"],
        (),
        None,
        ("market_implied", "market_implied"),
        ("market_implied", 7),
    )
    for steps in malformed:
        monkeypatch.setattr(cp3d.core, "STEP_IDS", steps)
        assert _refusal(cp3d.root, "market_implied") == "not_permitted", steps


def test_owner_scope_never_applies_to_a_live_contract_module(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An owner scope row for a module with a live step contract refuses, even with a core
    registered for it (so only the live-contract guard refuses); without the row the
    live-contract session opens exactly as before."""
    pack = _requested(runs.make_pack("positive"), "CP-1A")
    review = json.loads(runs.literal("positive", "readiness_review", pack))
    review["consumers"] = [c for c in review["consumers"] if c["module_id"] == "CP-1A"]
    _begun(tmp_path, pack, json.dumps(review))
    assert _pending(tmp_path).module_id == "CP-1A"
    assert _refusal(tmp_path, "business_context") == "opened"
    monkeypatch.setitem(owner._CORES, "CP-1A", _fake_core("CP-1A", "business_context"))
    assert _refusal(tmp_path, "business_context") == "opened"
    widened = {**host._OWNER_SCOPES, ("CP-1A", "business_context"): lambda _: ("identity",)}
    monkeypatch.setattr(host, "_OWNER_SCOPES", MappingProxyType(widened))
    monkeypatch.setattr(host, "SourceTools", _NoCapability)
    assert _refusal(tmp_path, "business_context") == "not_permitted"


def test_an_empty_owner_scope_is_not_refused(
    cp3d: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q6: CP-4's empty-scope refusal is CP-4's alone; an owner-only step whose pack holds none
    of its sources still opens (every read is then refused)."""
    empty = {**host._OWNER_SCOPES, ("CP-3D", "market_implied"): lambda _: ()}
    monkeypatch.setattr(host, "_OWNER_SCOPES", MappingProxyType(empty))
    store = Execution(cp3d.root / "store")
    session = SourceSession.from_execution(store, _pending(cp3d.root).ticket_id, "market_implied")
    call = session.invoke("read_pages", {"source_id": "market", "first_page": 1, "last_page": 1})
    assert (call["status"], call["error_code"]) == ("refused", "not_permitted")


# --- 3. the `*-submission` producer rule (Q6 (b)) and its memo ---------------------------------


def _cp1a_run(root: Path, *, valid: bool) -> tuple[Execution, ExecutionSnapshot, Module]:
    """Plan CP-0, CP-1A through the public API. `valid`: the S1 business_context judging the
    plan's only listed consumer (CP-MODEL; the CP-2 row is dropped, plan-shape test input) ->
    a settled head with its `business-context-submission` tail. Otherwise the unchanged literal
    twice (it judges CP-2, which this plan does not list) -> a blocked head."""
    pack = _requested(runs.make_pack("positive"), "CP-1A")
    review = json.loads(runs.literal("positive", "readiness_review", pack))
    review["consumers"] = [c for c in review["consumers"] if c["module_id"] == "CP-1A"]
    workflow = _begun(root, pack, json.dumps(review))
    literal = json.loads(runs.literal("positive", "business_context", pack))
    if valid:
        literal["consumers"] = [c for c in literal["consumers"] if c["module_id"] != "CP-2"]
    for _ in range(1 if valid else 2):
        outcome = runs.drive_cp1a(workflow, pack, "positive", text=json.dumps(literal))
        assert outcome["status"] == ("valid" if valid else "invalid")
    store = Execution(root / "store")
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-1A")
    assert head.status == ("restricted" if valid else "blocked")
    return store, snapshot, store.head_module(head)


def _forged(snapshot: ExecutionSnapshot, producer: Module, **update: Any) -> tuple[Any, Module]:
    """A producer changed by `update` and a snapshot whose producing attempt names its hash, so
    the rule selects the forgery and must refuse it on content."""
    forged = producer.model_copy(update=update)
    attempts = tuple(
        a.model_copy(update={"result_sha256": forged.content_hash()})
        if a.result_sha256 == producer.content_hash()
        else a
        for a in snapshot.attempts
    )
    return snapshot.model_copy(update={"attempts": attempts}), forged


def test_settled_cp1a_head_is_an_authentic_producer(tmp_path: Path) -> None:
    store, snapshot, producer = _cp1a_run(tmp_path, valid=True)
    tail = producer.inputs[-1]
    assert (tail.input_id, tail.status) == ("business-context-submission", "accepted")
    assert host._producer_inputs(store, snapshot, producer) is True


def test_forged_settled_tail_is_refused(tmp_path: Path) -> None:
    store, snapshot, producer = _cp1a_run(tmp_path, valid=True)
    prefix, tail = producer.inputs[:-1], producer.inputs[-1]
    variants = {
        "tail digest": (*prefix, tail.model_copy(update={"sha256": "0" * 64})),
        "tail id": (*prefix, tail.model_copy(update={"input_id": "business-context"})),
        "no tail": prefix,
        "two tails": (*prefix, tail, tail.model_copy(update={"input_id": "x-submission"})),
        "prefix": (Input(input_id="prepared-pack", sha256="0" * 64), *prefix[1:], tail),
    }
    for label, inputs in variants.items():
        forged_snapshot, forged = _forged(snapshot, producer, inputs=inputs)
        assert host._producer_inputs(store, forged_snapshot, forged) is False, label
    # The tail intact and the content forged: the settlement replay refuses it.
    forged_snapshot, forged = _forged(
        snapshot, producer, limitations=(*producer.limitations, "Forged limitation")
    )
    assert host._producer_inputs(store, forged_snapshot, forged) is False


def test_blocked_cp1a_head_is_accepted_without_a_tail(tmp_path: Path) -> None:
    """Q6: the failed-head branch keeps today's acceptance of a blocked producer (CP-3 under a
    blocked CP-1A, a restricted edge); a blocked head with a tail or forged issues is refused."""
    store, snapshot, producer = _cp1a_run(tmp_path, valid=False)
    expected = (
        Input(input_id="prepared-pack", sha256=snapshot.pack_sha256),
        next(i for i in producer.inputs if i.input_id == "CP-0"),
    )
    assert producer.inputs == expected
    assert host._producer_inputs(store, snapshot, producer) is True
    tail = Input(input_id="business-context-submission", sha256="0" * 64)
    variants: dict[str, dict[str, Any]] = {
        "tail": {"inputs": (*producer.inputs, tail)},
        "limitations": {"limitations": ("Forged issue",)},
        "status": {"status": "restricted"},
    }
    for label, update in variants.items():
        forged_snapshot, forged = _forged(snapshot, producer, **update)
        assert host._producer_inputs(store, forged_snapshot, forged) is False, label


def test_memo_skips_the_replay_but_rechecks_every_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q6 memo per (snapshot hash, producer hash): a hit replays nothing, yet re-reads and
    hash-checks every blob the pass read; a tampered one refuses as before."""
    store, snapshot, producer = _cp1a_run(tmp_path, valid=True)
    replays: list[str] = []

    def counted(*args: Any, **kwargs: Any) -> Any:
        replays.append(args[1].module_id)
        return settle(*args, **kwargs)

    monkeypatch.setattr(host, "settle", counted)
    assert host._producer_inputs(store, snapshot, producer) is True
    assert replays == ["CP-1A"]
    assert host._producer_inputs(store, snapshot, producer) is True
    assert replays == ["CP-1A"]
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == producer.content_hash())
    blob = store.directory / "blobs" / attempt.steps[0].payload_sha256
    blob.chmod(0o644)
    blob.write_bytes(blob.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        host._producer_inputs(store, snapshot, producer)
    assert replays == ["CP-1A"]


# --- 4. fix round 1: self-consistent forgeries and the memo (H1 review F2, L3, L4) -----------

Inputs = tuple[Input, ...]


def _cp1a_journal(
    root: Path,
    genuine: tuple[Execution, ExecutionSnapshot, Module],
    inputs: Callable[[Inputs, Inputs], Inputs],
    *,
    extra_step: bool = False,
) -> tuple[Execution, ExecutionSnapshot, Module]:
    """A self-consistent CP-1A head written through the public `Execution` API, so the settle
    replay reproduces it and only the Q6 (b) checks can refuse it: the genuine business_context
    payload journaled with a bypass validator (with `extra_step`, under a two-step sequence and a
    second step), then finished with the genuine candidate whose inputs are `inputs(attempt
    inputs, genuine tail)`."""
    from deploy_vii.business_context import PROMOTED

    g_store, g_snapshot, g_head = genuine
    g_attempt = next(a for a in g_snapshot.attempts if a.result_sha256 == g_head.content_hash())
    pack = _requested(runs.make_pack("positive"), "CP-1A")
    review = json.loads(runs.literal("positive", "readiness_review", pack))
    review["consumers"] = [c for c in review["consumers"] if c["module_id"] == "CP-1A"]
    _begun(root, pack, json.dumps(review))
    store = Execution(root / "store")
    attempt = _pending(root)
    sequence = ("business_context", "h1_extra") if extra_step else ("business_context",)

    def bypass(_pack: PreparedPack, _attempt: Attempt) -> StepValidation:
        return StepValidation(output="bypass: no composer ran")

    payloads = (g_store.payload(g_attempt.steps[0].payload_sha256), "{}")
    for step_id, payload in zip(sequence, payloads, strict=False):
        store.submit_step(attempt.ticket_id, "CP-1A", sequence, step_id, payload, bypass)
    candidate = json.loads(g_store.payload(g_attempt.payload_sha256 or ""))
    tail = g_head.inputs[len(g_attempt.inputs) :]
    candidate["inputs"] = [i.model_dump(mode="json") for i in inputs(attempt.inputs, tail)]
    text = Module.model_validate_json(json.dumps(candidate)).model_dump_json()
    finished = store.finish(attempt.ticket_id, text, lambda _: (), qualification=PROMOTED)
    assert finished.status == "finished" and not finished.issues
    assert len(finished.steps) == len(sequence)
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-1A")
    return store, snapshot, store.head_module(head)


def _unchanged(prefix: Inputs, tail: Inputs) -> Inputs:
    return (*prefix, *tail)


def _tail_digest(prefix: Inputs, tail: Inputs) -> Inputs:
    return (*prefix, tail[0].model_copy(update={"sha256": "0" * 64}))


def _tail_id(prefix: Inputs, tail: Inputs) -> Inputs:
    return (*prefix, tail[0].model_copy(update={"input_id": "business-context"}))


def _two_tails(prefix: Inputs, tail: Inputs) -> Inputs:
    return (*prefix, tail[0], tail[0].model_copy(update={"input_id": "x-submission"}))


def _reordered(prefix: Inputs, tail: Inputs) -> Inputs:
    return (*reversed(prefix), *tail)


def test_self_consistent_forgeries_reach_each_q6_check(tmp_path: Path) -> None:
    """F2: each forgery is settled by the real journal, so the settle replay reproduces it and
    only its named Q6 (b) check can refuse it. The unchanged journal passes, so each refusal
    is that check's: one tail input, a `*-submission` id, the retained submission's digest,
    the bound prefix in order, and a one-step attempt."""
    genuine = _cp1a_run(tmp_path / "genuine", valid=True)
    store, snapshot, control = _cp1a_journal(tmp_path / "control", genuine, _unchanged)
    assert host._producer_inputs(store, snapshot, control) is True
    variants: dict[str, tuple[Callable[[Inputs, Inputs], Inputs], bool]] = {
        "tail digest": (_tail_digest, False),
        "tail id": (_tail_id, False),
        "two tails": (_two_tails, False),
        "reordered prefix": (_reordered, False),
        "two-step attempt": (_unchanged, True),
    }
    for label, (inputs, extra_step) in variants.items():
        root = tmp_path / label.replace(" ", "-")
        store, snapshot, forged = _cp1a_journal(root, genuine, inputs, extra_step=extra_step)
        assert host._producer_inputs(store, snapshot, forged) is False, label


def test_producer_without_a_producing_attempt_refuses(tmp_path: Path) -> None:
    """L3: a head whose producing attempt the snapshot does not hold is refused, not an
    `IndexError` (which `_execution_state` would not map)."""
    store, snapshot, producer = _cp1a_run(tmp_path, valid=True)
    orphan = snapshot.model_copy(
        update={
            "attempts": tuple(
                a for a in snapshot.attempts if a.result_sha256 != producer.content_hash()
            )
        }
    )
    assert host._producer_inputs(store, orphan, producer) is False


def _memo_key(snapshot: ExecutionSnapshot, producer: Module) -> tuple[str, str]:
    """The Q6 memo key: (snapshot hash, producer result hash)."""
    digest = hashlib.sha256(snapshot.model_dump_json().encode()).hexdigest()
    return digest, producer.content_hash()


def test_memo_keeps_passes_only(tmp_path: Path) -> None:
    """L4: a refusal is never kept, so asking again refuses again and the memo stays empty."""
    genuine = _cp1a_run(tmp_path / "genuine", valid=True)
    store, snapshot, forged = _cp1a_journal(tmp_path / "forged", genuine, _tail_digest)
    assert host._producer_inputs(store, snapshot, forged) is False
    assert host._producer_inputs(store, snapshot, forged) is False
    assert host._SUBMISSION_VERIFIED == {}


def test_memo_key_is_the_snapshot_and_the_producer(tmp_path: Path) -> None:
    """L4: a cached pass is served only for its own (snapshot, producer): another producer under
    the cached snapshot, and the cached producer under another snapshot, are verified afresh."""
    store, snapshot, producer = _cp1a_run(tmp_path, valid=True)
    assert host._producer_inputs(store, snapshot, producer) is True
    assert set(host._SUBMISSION_VERIFIED) == {_memo_key(snapshot, producer)}
    tail = producer.inputs[-1]
    other = producer.model_copy(
        update={"inputs": (*producer.inputs[:-1], tail.model_copy(update={"sha256": "1" * 64}))}
    )
    assert host._producer_inputs(store, snapshot, other) is False
    orphan = snapshot.model_copy(
        update={
            "attempts": tuple(
                a for a in snapshot.attempts if a.result_sha256 != producer.content_hash()
            )
        }
    )
    assert host._producer_inputs(store, orphan, producer) is False
    assert set(host._SUBMISSION_VERIFIED) == {_memo_key(snapshot, producer)}


def test_memo_evicts_the_oldest_pass_beyond_its_limit(tmp_path: Path) -> None:
    """L4: the memo holds at most 16 passes; the oldest is evicted first."""
    store, snapshot, producer = _cp1a_run(tmp_path, valid=True)
    limit = 16
    assert host._SUBMISSION_VERIFIED_LIMIT == limit
    # Passing snapshots that differ only in `parent`: each is its own key.
    variants = [snapshot.model_copy(update={"parent": f"{i:064x}"}) for i in range(limit + 4)]
    for variant in variants:
        assert host._producer_inputs(store, variant, producer) is True
    assert list(host._SUBMISSION_VERIFIED) == [_memo_key(v, producer) for v in variants[4:]]
