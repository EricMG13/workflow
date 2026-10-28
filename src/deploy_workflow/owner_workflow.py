"""Plan-driven offline owner workflow: one adapter for every declared owner spec.

Execution and the adopted owner cores own every calculation and settlement. This
adapter owns finite capabilities, immutable participation evidence and the receipt.
It generalises `financial_workflow` (which stays the reference and is imported, never
edited): the walk follows `registry.plan`, each module's steps come from a declared
`OwnerSpec`, and paths are supplied by trusted setup, never by a message.
G1 shipped CP-0, CP-1 and CP-MODEL; S1a adds CP-1A and CP-2 (their probes and the CP-2
read view live in `deploy_workflow.owners`). G1-X (`docs/G1X-OWNER-CORE-PROTOCOL.md`) serves
owner cores: an owner-only module (no live step contract) is entered through its registered
core (`_CORES`), any module may register a precheck gate (`_PRECHECKS`), and every module with
a `_VIEWS` entry may be read through `module_context`. No durable resume exists (an
interrupted run is refused and a new run starts).
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from types import MappingProxyType, ModuleType
from typing import Any, Literal, TextIO
from uuid import uuid4

from deploy_vii.business_context import PROMOTED as CP1A_PROMOTED
from deploy_vii.contracts import Contract, Hash, Identifier, Input, Module, Run
from deploy_vii.cp0_workflow import _validate_review as cp0_validate_review
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.cp1_workflow import PROMOTED, _quality_stage, validate_cp1_stage
from deploy_vii.cp2_synthesis import PROMOTED as CP2_PROMOTED
from deploy_vii.cp_model_workflow import (
    PUBLISHED,
    CpModelRefused,
    publish_cp_model,
    verify_cp_model_publication,
)
from deploy_vii.execution import (
    WITHIN_ATTEMPT_REPAIR,
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    NotAuthorized,
    StepSubmission,
    StepValidation,
    bounded_issues,
    current_inputs,
    head_of,
    settle,
    text_sha256,
)
from deploy_vii.live.schema import normalise
from deploy_vii.live.submission import (
    PREFILLED,
    STEPS,
    Submitted,
    _validate_prefilled,
    known_bindings,
    prefill,
    submit_model_payload,
)
from deploy_vii.live.tools import ToolRules
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import StepChain, dependencies, plan, step_chain
from deploy_workflow import host
from deploy_workflow.financial_workflow import (
    FILES,
    MAX_CALLS,
    MAX_LINE,
    MAX_MESSAGES,
    FinancialBinding,
    ModelPublication,
    PublicationCall,
    _evidence_issues,
    _files,
    _filled,
    _FrozenExecution,
    _hash,
    _historical,
    _nonfinite_json,
    _parse,
    _projection,
    _put,
    _record,
    _snapshot,
    _verify_cp0,
    _verify_model_settlement,
    _verify_promotion,
)
from deploy_workflow.host import SourceSession
from deploy_workflow.owners import cp1a, cp2
from deploy_workflow.tools.source import SourceError
from deploy_workflow.workflow import SourceEvidence, WorkflowError

AUDIT = "owner-run-audit"
SUPPORTED_ANALYTICAL = frozenset({"CP-0", "CP-1", "CP-1A", "CP-2"})
BLOCKED_EDGE = "Required upstream is unrun, stale or blocked"
# G1-X §2: the fixed owner-core registry, one row per owner-only module (`registry.step_chain`
# raises "has no live step contract"). Never caller-supplied; module tasks add their rows. A core
# supplies `STEP_IDS`, `SCHEMAS`, `submit` and, for steps with pack sources, `RULES`.
_CORES: dict[str, ModuleType] = {}
_QUALIFICATION = {
    "CP-1": PROMOTED,
    "CP-1A": CP1A_PROMOTED,
    "CP-2": CP2_PROMOTED,
    "CP-MODEL": PUBLISHED,
}
_PROBES: dict[str, Callable[[Execution, ExecutionSnapshot, Attempt], None]] = {
    "CP-0": _verify_cp0,
    "CP-1": _verify_promotion,
    "CP-1A": cp1a.probe,
    "CP-2": cp2.probe,
}
# The exact `read_inputs` view of each `module_context` step (S1a lease rev 2, M4; G1-X §3: any
# step with an entry here may declare `inputs="module_context"`).
_VIEWS: dict[str, Callable[[Execution, Attempt], tuple[str, str]]] = {
    "credit_synthesis": cp2.view,
}
# The validator each module's own entry hands `Execution.submit_step`: the verifier replays an
# invalid step through it at the historical snapshot (S1a R4-2). Module tasks add their rows;
# every analytical module but CP-0 and CP-1 needs one, or create refuses it (G1-X §2).
_ENTRY_VALIDATORS: dict[str, Callable[[Execution, PreparedPack, Attempt], StepValidation]] = {
    "CP-1A": cp1a.ENTRY_VALIDATOR,
    "CP-2": cp2.ENTRY_VALIDATOR,
}
# CP-0 and CP-1 keep the reused financial helpers, which are bound to their 11-field binding.
_FINANCIAL_MODULES = frozenset({"CP-0", "CP-1"})


@dataclass(frozen=True)
class StepSpec:
    """One journal step. `sources`: pack tools (SourceSession); `extract`: statement
    extraction is offered; `upstream_grant`: frozen-upstream grant (none yet);
    `inputs`: `projection` lets `read_inputs` return the adopted CP-1 view and
    `module_context` the step's exact view (its `_VIEWS` entry); any `inputs` other than
    `none` must be read before the step is submitted, with or without a source session;
    `rules`: `precheck` applies the evidence rules of `financial_workflow._evidence_issues`
    before the journal (a failing submit is refused and writes nothing; CP-0 and CP-1 only);
    `journaled` hands the tool-loop rules to the journal (a failing submit is retained as an
    invalid step): `ToolRules` for a live-contract step, the core's `RULES` for an owner-only
    one. A module's `_PRECHECKS` gate runs before either mode (G1-X §4)."""

    step_id: str
    schema: type[Contract]
    sources: bool
    extract: bool
    upstream_grant: Mapping[str, Any] | None
    inputs: Literal["none", "projection", "module_context"]
    rules: Literal["none", "precheck", "journaled"]


@dataclass(frozen=True)
class OwnerSpec:
    module_id: str
    steps: tuple[StepSpec, ...]
    entry: Literal["cp0_review", "model_payload", "owner_core"] | None
    kind: Literal["analytical", "deterministic"]
    publish: Callable[..., Attempt] | None


def _default_specs() -> dict[str, OwnerSpec]:
    from deploy_vii.business_context import BusinessContextSubmission
    from deploy_vii.cp1_workflow import FinancialSubmission
    from deploy_vii.cp2_synthesis import CreditSynthesisSubmission
    from deploy_vii.downstream_readiness import DownstreamReview
    from deploy_vii.narrative import NarrativeReview
    from deploy_vii.quality import QualityReview
    from deploy_vii.readiness import ReadinessReview
    from deploy_vii.source_context import SourceContextReview

    def step(
        step_id: str,
        schema: type[Contract],
        *,
        sources: bool = False,
        extract: bool = False,
        inputs: Literal["none", "projection", "module_context"] = "none",
        rules: Literal["none", "precheck", "journaled"] = "none",
    ) -> StepSpec:
        return StepSpec(
            step_id=step_id,
            schema=schema,
            sources=sources,
            extract=extract,
            upstream_grant=None,
            inputs=inputs,
            rules=rules,
        )

    return {
        "CP-0": OwnerSpec(
            module_id="CP-0",
            steps=(step("source_readiness", ReadinessReview, sources=True, rules="precheck"),),
            entry="cp0_review",
            kind="analytical",
            publish=None,
        ),
        "CP-1": OwnerSpec(
            module_id="CP-1",
            steps=(
                step("source_context", SourceContextReview, sources=True, rules="precheck"),
                step(
                    "financials",
                    FinancialSubmission,
                    sources=True,
                    extract=True,
                    rules="precheck",
                ),
                step("narrative", NarrativeReview, inputs="projection"),
                step("readiness", DownstreamReview, inputs="projection"),
                step("quality", QualityReview, inputs="projection"),
            ),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-1A": OwnerSpec(
            module_id="CP-1A",
            steps=(
                step(
                    "business_context",
                    BusinessContextSubmission,
                    sources=True,
                    rules="journaled",
                ),
            ),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-2": OwnerSpec(
            module_id="CP-2",
            steps=(step("credit_synthesis", CreditSynthesisSubmission, inputs="module_context"),),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-MODEL": OwnerSpec(
            module_id="CP-MODEL",
            steps=(),
            entry=None,
            kind="deterministic",
            publish=publish_cp_model,
        ),
    }


OWNER_SPECS: Mapping[str, OwnerSpec] = MappingProxyType(_default_specs())


class OwnerBinding(Contract):
    run_id: Identifier
    issuer_id: Identifier
    as_of: str
    method_version: str
    pack_sha256: Hash
    snapshot_sha256: Hash
    module_id: Identifier
    step_id: Identifier
    ticket_id: Identifier
    attempt: int
    inputs: tuple[Input, ...]


# G1-X §4: a module's optional precheck gate, `precheck(store, binding, stored)` over the filled
# payload. Issues refuse the submission before any rule and before the journal; the verifier
# recomputes it for every submission. Module tasks add their rows (live-contract or owner-only).
_PRECHECKS: dict[str, Callable[[Execution, OwnerBinding, str], tuple[str, ...]]] = {}


class OwnerCall(Contract):
    schema_version: Literal["tool-receipt/1"]
    call_id: str
    sequence: int
    binding: OwnerBinding
    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "refused", "error"]
    body: str | None
    error_code: str | None
    source_evidence: SourceEvidence


class OwnerInputRead(Contract):
    binding: OwnerBinding
    sequence: int
    operation: Literal["read_inputs"] = "read_inputs"
    inputs_sha256: Hash
    body: str


class OwnerSubmissionBinding(Contract):
    schema_version: Literal["submission-binding/1"] = "submission-binding/1"
    binding: OwnerBinding
    payload_sha256: Hash
    successful_call_ids: tuple[str, ...]
    call_ids: tuple[str, ...]
    source_evidence: SourceEvidence


class OwnerSubmission(Contract):
    sequence: int
    binding: OwnerSubmissionBinding
    stored_payload_sha256: Hash
    canonical_review_sha256: Hash | None
    disposition: Literal["valid", "invalid", "refused"]
    issues: tuple[str, ...]
    snapshot_after_sha256: Hash
    nulls_resolved: tuple[str, ...] = ()
    prefilled: tuple[str, ...] = ()
    prefilled_kinds: tuple[str, ...] = ()
    step_sha256: Hash | None = None
    step_output_sha256: Hash | None = None


class BeginRecord(Contract):
    module_id: Identifier
    ticket_id: Identifier
    attempt: int
    snapshot_before_sha256: Hash
    snapshot_after_sha256: Hash


class RefusedBegin(Contract):
    module_id: Identifier
    snapshot_sha256: Hash
    reason: str


class SettledHead(Contract):
    module_id: Identifier
    ticket_id: Identifier
    result_sha256: Hash
    status: Literal["accepted", "restricted", "blocked"]


class OwnerRunReceipt(Contract):
    schema_version: Literal["owner-run-receipt/1"] = "owner-run-receipt/1"
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    participant: str
    transport: Literal["python-api", "bounded-json-lines/1"]
    plan: tuple[str, ...]
    heads: tuple[SettledHead, ...]
    model: ModelPublication | None
    begins: tuple[BeginRecord, ...]
    refusals: tuple[RefusedBegin, ...]
    calls: tuple[OwnerCall, ...]
    input_reads: tuple[OwnerInputRead, ...]
    submissions: tuple[OwnerSubmission, ...]
    publications: tuple[PublicationCall, ...]


def _fin(binding: OwnerBinding) -> FinancialBinding:
    """The reused CP-0/CP-1 helpers take the 11-field binding with literal module ids."""
    return FinancialBinding.model_validate(binding.model_dump())


def _owner_binding(snapshot: ExecutionSnapshot, attempt: Attempt, step_id: str) -> OwnerBinding:
    """The same 11 fields as `financial_workflow._binding`, without its CP-0/CP-1 literal."""
    return _parse(
        OwnerBinding,
        {
            "run_id": snapshot.run.run_id,
            "issuer_id": snapshot.run.issuer_id,
            "as_of": snapshot.run.as_of.isoformat(),
            "method_version": snapshot.run.method_version,
            "pack_sha256": snapshot.pack_sha256,
            "snapshot_sha256": snapshot.content_hash(),
            "module_id": attempt.module_id,
            "step_id": step_id,
            "ticket_id": attempt.ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
        },
    )


def _attempt_of(snapshot: ExecutionSnapshot, ticket_id: str) -> Attempt:
    """The snapshot's attempt of `ticket_id`; evidence naming another ticket does not bind (R4-4:
    a tamper cause, never a raw lookup failure)."""
    attempt = next((a for a in snapshot.attempts if a.ticket_id == ticket_id), None)
    if attempt is None:
        raise WorkflowError("identity_mismatch")
    return attempt


def _result_attempt(snapshot: ExecutionSnapshot, head: Head) -> Attempt:
    """The snapshot's attempt that settled `head` (R4-4, as `_attempt_of`)."""
    attempt = next((a for a in snapshot.attempts if a.result_sha256 == head.result_sha256), None)
    if attempt is None:
        raise WorkflowError("identity_mismatch")
    return attempt


def _sequence(module_id: str) -> tuple[str, ...]:
    """The module's journal step sequence: its live step contract, or its owner core's
    `STEP_IDS` where `step_chain` has none (G1-X §2). An owner-only module without a core is a
    registration error and raises `KeyError` (`_check_specs` refuses it before any run)."""
    try:
        return step_chain(module_id).steps
    except ValueError:
        steps: tuple[str, ...] = tuple(_CORES[module_id].STEP_IDS)
        return steps


def _owner_historical(store: Execution, binding: OwnerBinding) -> _FrozenExecution:
    """`financial_workflow._historical` for any other module: its step sequence (the live step
    chain, else the owner core's `STEP_IDS`) is the sequence."""
    snapshot = _snapshot(store, binding.snapshot_sha256)
    attempt = _attempt_of(snapshot, binding.ticket_id)
    sequence = _sequence(attempt.module_id)
    if (
        _owner_binding(snapshot, attempt, binding.step_id) != binding
        or attempt.status != "pending"
        or attempt.issues
        or attempt.interruption
        or attempt.payload_sha256 is not None
        or attempt.result_sha256 is not None
        or current_inputs(snapshot, attempt.module_id) != attempt.inputs
        or tuple(s.step_id for s in attempt.steps) != sequence[: len(attempt.steps)]
        or any(s.status != "valid" for s in attempt.steps)
        or len(attempt.steps) >= len(sequence)
        or sequence[len(attempt.steps)] != binding.step_id
    ):
        raise WorkflowError("identity_mismatch")
    return _FrozenExecution(store, snapshot)


def _hist(store: Execution, binding: OwnerBinding) -> _FrozenExecution:
    if binding.module_id in _FINANCIAL_MODULES:
        # R4-4: the reused helper looks the ticket up unguarded; an absent one is checked first.
        _attempt_of(_snapshot(store, binding.snapshot_sha256), binding.ticket_id)
        return _historical(store, _fin(binding))
    return _owner_historical(store, binding)


def _fill(
    store: Execution, binding: OwnerBinding, payload: str
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """What the journal retains: CP-0/CP-1 as `_filled`; any other step as the entry path of
    `live.submission.submit_model_payload` (null resolution, no pre-fill), against the live
    schema of its step or, for a step outside `live.submission.STEPS`, its owner core's
    `SCHEMAS` entry (G1-X §2)."""
    if binding.module_id in _FINANCIAL_MODULES:
        return _filled(store, _fin(binding), payload)
    step_id = binding.step_id
    schema = (
        STEPS[step_id].schema if step_id in STEPS else _CORES[binding.module_id].SCHEMAS[step_id]
    )
    normal, resolved = normalise(schema, payload)
    return normal, resolved, (), ()


def _journaled_issues(
    module_id: str, step_id: str, payload: str, evidence: SourceEvidence
) -> tuple[str, ...]:
    """The tool-use rules of a `journaled` step over the session's `Seen`: `ToolRules` (absence
    and unread citations) for a live-contract step; the owner core's `RULES(text, seen)` for an
    owner-only one, where `ToolRules` raises (G1-X §2, LEAD amendment 2026-10-28)."""
    core = _CORES.get(module_id)
    if core is None:
        return ToolRules().issues(step_id, payload, seen=evidence.seen(), context=None)
    found: tuple[str, ...] = tuple(core.RULES(payload, evidence.seen()))
    return found


def _gate(
    store: Execution,
    binding: OwnerBinding,
    spec: StepSpec,
    stored: str,
    evidence: SourceEvidence,
) -> tuple[str, ...]:
    """The issues that refuse a submission before the journal, recomputed alike at submit and in
    the verifier: the module's precheck gate over the filled payload first (G1-X §4), then, only
    when the gate passes, the `precheck`-mode evidence rules. The journaled rules come later.
    The gate sees the same read-only view of the binding's snapshot at submit and in replay."""
    precheck = _PRECHECKS.get(binding.module_id)
    issues: tuple[str, ...] = ()
    if precheck is not None:
        frozen = _FrozenExecution(store, _snapshot(store, binding.snapshot_sha256))
        issues = bounded_issues(tuple(precheck(frozen, binding, stored)))
    if not issues and spec.rules == "precheck":
        issues = _evidence_issues(store, _fin(binding), stored, evidence)
    return issues


def _inputs(store: Execution, binding: OwnerBinding, spec: StepSpec) -> tuple[str, str]:
    """The (sha256, body) `read_inputs` returns for `spec`, recomputed from the journal."""
    if spec.inputs == "projection":
        return _projection(store, _fin(binding))
    if spec.inputs == "module_context":
        historical = _owner_historical(store, binding)
        return _VIEWS[spec.step_id](historical, _attempt_of(historical.read(), binding.ticket_id))
    raise WorkflowError("not_permitted")


def _terminal(heads: tuple[Head, ...], run: Run, publisher: str) -> bool:
    """Publication is terminal when a producer the publisher requires holds no accepted or
    restricted head. A refusal or a blocked head further down the walk does not make it so."""
    settled = {h.module_id for h in heads if h.status in ("accepted", "restricted")}
    return not dependencies(run.requested_modules)[publisher] <= settled


def _audit(store: Execution, kind: str, digest: str) -> Path:
    return store.directory / AUDIT / kind / digest


def _retain(store: Execution, kind: str, value: Contract) -> None:
    _put(_audit(store, kind, value.content_hash()), value.model_dump_json().encode())


def _raw(store: Execution, digest: str) -> str:
    raw = _audit(store, "payloads", digest).read_bytes()
    if _hash(raw) != digest:
        raise WorkflowError("identity_mismatch")
    return raw.decode("utf-8")


def _settled(store: Execution, module_id: str) -> SettledHead:
    snapshot = store.read()
    head = next((h for h in snapshot.heads if h.module_id == module_id), None)
    if head is None:
        raise WorkflowError("identity_mismatch")
    attempt = _result_attempt(snapshot, head)
    if attempt.status != "finished" or (head.status != "blocked" and attempt.issues):
        raise WorkflowError("identity_mismatch")
    if head.status not in ("accepted", "restricted", "blocked"):
        raise WorkflowError("identity_mismatch")
    return SettledHead(
        module_id=module_id,
        ticket_id=attempt.ticket_id,
        result_sha256=head.result_sha256,
        status=head.status,
    )


def _step(specs: Mapping[str, OwnerSpec], module_id: str, step_id: str) -> StepSpec:
    """The declared step; a recorded binding naming no declared step does not bind (R4-4)."""
    spec = specs.get(module_id)
    found = None if spec is None else next((s for s in spec.steps if s.step_id == step_id), None)
    if found is None:
        raise WorkflowError("identity_mismatch")
    return found


def _check_steps(module_id: str, spec: OwnerSpec) -> None:
    """The reference spec of one analytical module is one G1-X can serve (protocol §1-§3).

    The entry is the one `submit_review` and `_entry_outcome` dispatch for the module:
    `cp0_review` for CP-0, `model_payload` for any other live-contract module, `owner_core` for
    an owner-only one (`step_chain` raises "has no live step contract"). Every module but CP-0
    and CP-1 has an `_ENTRY_VALIDATORS` row (§2). A live-contract module keeps its registry
    chain and the chain's pack and extraction tools. An owner-only module has a registered,
    complete core: `STEP_IDS` (nonempty and distinct, as `Execution.submit_step` requires) are
    its steps (a tuple of str), `SCHEMAS[step]` is each step's schema, `submit` is callable and so is `RULES`
    when a step is journaled. Its step ids stay outside `live.submission.STEPS` (so `_fill`
    reads the core's `SCHEMAS`), it offers no statement extraction, a step has pack sources exactly when `host._OWNER_SCOPES`
    has its row, and a `journaled` step has pack sources (`RULES` judges the session's `Seen`). Every step: no upstream grant, some
    evidence (pack sources or a read), `module_context` only with a `_VIEWS` entry, and the
    financial `precheck` rules and CP-1 projection only on CP-0/CP-1, whose binding they
    take."""
    core = _CORES.get(module_id)
    try:
        chain: StepChain | None = step_chain(module_id)
    except ValueError:
        chain = None
    entry = (
        "owner_core" if chain is None else "cp0_review" if module_id == "CP-0" else "model_payload"
    )
    if (
        spec.entry != entry
        or (core is None) == (chain is None)
        or (module_id not in _FINANCIAL_MODULES and module_id not in _ENTRY_VALIDATORS)
    ):
        raise WorkflowError("not_permitted")
    if chain is None:
        schemas = getattr(core, "SCHEMAS", {})
        if (
            not callable(getattr(core, "submit", None))
            or (
                any(s.rules == "journaled" for s in spec.steps)
                and not callable(getattr(core, "RULES", None))
            )
            or any(schemas.get(s.step_id) is not s.schema for s in spec.steps)
        ):
            raise WorkflowError("not_permitted")
        raw = getattr(core, "STEP_IDS", ())
        if type(raw) is not tuple or not all(type(i) is str for i in raw):
            raise WorkflowError("not_permitted")
        sequence = raw
    else:
        sequence = chain.steps
    # `Execution.submit_step` takes only a nonempty, duplicate-free sequence.
    if (
        not sequence
        or len(set(sequence)) != len(sequence)
        or tuple(s.step_id for s in spec.steps) != sequence
    ):
        raise WorkflowError("not_permitted")
    for item in spec.steps:
        if chain is None:
            served = (
                item.step_id not in STEPS
                and not item.extract
                and (item.rules != "journaled" or item.sources)
                and item.sources == ((module_id, item.step_id) in host._OWNER_SCOPES)
            )
        else:
            served = item.sources == (item.step_id in chain.pack_sources) and item.extract == (
                item.step_id in chain.extract_tools
            )
        if (
            not served
            or item.upstream_grant is not None  # grant calls are not verifiable in G1
            or (not item.sources and item.inputs == "none")
            or (item.inputs == "module_context" and item.step_id not in _VIEWS)
            or (
                module_id not in _FINANCIAL_MODULES
                and (item.rules == "precheck" or item.inputs == "projection")
            )
        ):
            raise WorkflowError("not_permitted")


def _check_specs(
    pack: PreparedPack,
    specs: Mapping[str, OwnerSpec],
    publication_directory: Path | None,
    directory: Path,
) -> tuple[str, ...]:
    """Every refusal happens before anything is written."""
    try:
        planned = plan(pack.run.requested_modules)
    except ValueError:
        raise WorkflowError("not_permitted") from None
    seen_deterministic = False
    for module_id, extra in specs.items():
        if module_id not in planned and (
            module_id not in OWNER_SPECS or extra != OWNER_SPECS[module_id]
        ):
            raise WorkflowError("not_permitted")
    for module_id in planned:
        spec = specs.get(module_id)
        if spec is None or spec.module_id != module_id:
            raise WorkflowError("not_permitted")
        # rules, schemas and publishers are not caller-tunable
        if spec != OWNER_SPECS.get(module_id):
            raise WorkflowError("not_permitted")
        if spec.kind == "deterministic":
            # ponytail: unreachable while OWNER_SPECS holds one deterministic module;
            # guards a future second one
            if seen_deterministic or spec.steps or spec.entry is not None or spec.publish is None:
                raise WorkflowError("not_permitted")
            seen_deterministic = True
            continue
        if seen_deterministic or module_id not in SUPPORTED_ANALYTICAL or spec.publish:
            raise WorkflowError("not_permitted")
        _check_steps(module_id, spec)
    if any(OWNER_SPECS[m].kind == "deterministic" for m in planned):
        out = publication_directory
        if (
            out is None
            or out.exists()
            or out.resolve() == directory.resolve()
            or directory.resolve() in out.resolve().parents
        ):
            raise WorkflowError("not_permitted")
    return planned


class OwnerWorkflow:
    def __init__(
        self,
        store: Execution,
        planned: tuple[str, ...],
        publication_directory: Path | None,
    ) -> None:
        # Bind to the reference specs, never to the caller's mapping (checked at create).
        self._specs: Mapping[str, OwnerSpec] = MappingProxyType(
            {m: OWNER_SPECS[m] for m in planned}
        )
        self._store, self._plan = store, planned
        self._publication_directory = publication_directory
        self._operation = Lock()
        self._calls: list[OwnerCall] = []
        self._reads: list[OwnerInputRead] = []
        self._submissions: list[OwnerSubmission] = []
        self._publications: list[PublicationCall] = []
        self._begins: list[BeginRecord] = []
        self._refusals: list[RefusedBegin] = []
        self._refusal_kind: Literal["not_authorized", "blocked"] | None = None
        self._model: ModelPublication | None = None
        self._participant = "trusted-python"
        self._transport: Literal["python-api", "bounded-json-lines/1"] = "python-api"
        self._limits: Counter[tuple[str, str, str]] = Counter()
        self._analytical = tuple(m for m in planned if self._specs[m].kind == "analytical")
        self._phase = "analytical"  # analytical | walked | complete | failed
        self._sealed = False
        self._epoch_calls: list[OwnerCall] = []
        self._session: SourceSession | None = None
        self._spec: StepSpec
        self._binding: OwnerBinding
        self._current_sha256 = ""
        self._begin(self._analytical[0])

    @classmethod
    def create(
        cls,
        directory: Path,
        pack: PreparedPack,
        *,
        specs: Mapping[str, OwnerSpec] = OWNER_SPECS,
        publication_directory: Path | None = None,
    ) -> "OwnerWorkflow":
        planned = _check_specs(pack, specs, publication_directory, directory)
        if not any(OWNER_SPECS[m].kind == "analytical" for m in planned):
            raise WorkflowError("not_permitted")
        return cls(Execution.create(directory, pack), planned, publication_directory)

    @property
    def _refused(self) -> bool:
        """Publication is terminal (H1): CP-MODEL's required producer has no settled head."""
        snapshot = self._store.read()
        publisher = next((m for m in self._plan if self._specs[m].kind == "deterministic"), None)
        return publisher is not None and _terminal(snapshot.heads, snapshot.run, publisher)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        if not self._operation.acquire(blocking=False):
            raise WorkflowError("not_permitted")
        try:
            if self._sealed:
                raise WorkflowError("not_permitted")
            yield
        finally:
            self._operation.release()

    def _current(self) -> ExecutionSnapshot:
        snapshot = self._store.read()
        if snapshot.content_hash() != self._current_sha256:
            raise WorkflowError("stale_binding")
        self._store.pack(snapshot)
        return snapshot

    def _activate(self, attempt: Attempt, step_id: str) -> None:
        snapshot = self._store.read()
        self._spec = _step(self._specs, attempt.module_id, step_id)
        self._binding = _owner_binding(snapshot, attempt, step_id)
        self._current_sha256 = snapshot.content_hash()
        self._session = (
            SourceSession.from_execution(self._store, attempt.ticket_id, step_id)
            if self._spec.sources
            else None
        )
        self._epoch_calls = []
        _hist(self._store, self._binding)

    def _begin(self, module_id: str) -> bool:
        """Begin one analytical module; a refusal is retained and ends the walk."""
        before = self._store.read()
        kind: Literal["not_authorized", "blocked"]
        try:
            attempt = self._store.begin(module_id)
        except NotAuthorized as error:
            reason, kind = str(error), "not_authorized"
        except ValueError as error:
            # Only the blocked-edge refusal after a blocked producer is a retained refusal.
            if not str(error).startswith(BLOCKED_EDGE) or not any(
                h.status == "blocked" for h in before.heads
            ):
                raise
            reason, kind = str(error), "blocked"
        else:
            after = self._store.read()
            record = BeginRecord(
                module_id=module_id,
                ticket_id=attempt.ticket_id,
                attempt=attempt.number,
                snapshot_before_sha256=before.content_hash(),
                snapshot_after_sha256=after.content_hash(),
            )
            _retain(self._store, "begins", record)
            self._begins.append(record)
            self._activate(attempt, self._specs[module_id].steps[0].step_id)
            return True
        refusal = RefusedBegin(
            module_id=module_id, snapshot_sha256=before.content_hash(), reason=reason
        )
        _retain(self._store, "refused-begin", refusal)
        self._refusals.append(refusal)
        self._refusal_kind = kind
        self._current_sha256 = before.content_hash()
        self._finish_walk()
        return False

    def _advance(self, module_id: str) -> None:
        """Move past a settled or blocked module to the next planned analytical one."""
        later = self._analytical[self._analytical.index(module_id) + 1 :]
        if later:
            self._begin(later[0])
        else:
            self._finish_walk()

    def _finish_walk(self) -> None:
        self._phase = "walked"
        if all(self._specs[m].kind == "analytical" for m in self._plan):
            self._phase = "complete"

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            self._current()
            key = (self._binding.ticket_id, self._binding.step_id, "invoke")
            if self._phase != "analytical" or self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            if self._session is None:
                call = OwnerCall(
                    schema_version="tool-receipt/1",
                    call_id=str(uuid4()),
                    sequence=len(self._epoch_calls) + 1,
                    binding=self._binding,
                    tool=tool_name,
                    arguments=arguments,
                    status="refused",
                    body=None,
                    error_code="not_permitted",
                    source_evidence=SourceEvidence(),
                )
            else:
                call = _parse(OwnerCall, self._session.invoke(tool_name, arguments))
            call = _parse(OwnerCall, call.model_dump(mode="json"))
            if call.binding != self._binding or call.sequence != len(self._epoch_calls) + 1:
                raise WorkflowError("identity_mismatch")
            _retain(self._store, "calls", call)
            self._epoch_calls.append(call)
            self._calls.append(call)
            return call.model_dump(mode="json")

    def read_inputs(self) -> dict[str, Any]:
        with self._locked():
            self._current()
            key = (self._binding.ticket_id, self._binding.step_id, "read_inputs")
            if (
                self._phase != "analytical"
                or self._spec.inputs == "none"
                or self._limits[key] >= MAX_CALLS
            ):
                raise WorkflowError("not_permitted")
            digest, body = _inputs(self._store, self._binding, self._spec)
            self._limits[key] += 1
            record = OwnerInputRead(
                binding=self._binding, sequence=self._limits[key], inputs_sha256=digest, body=body
            )
            _retain(self._store, "input-reads", record)
            self._reads.append(record)
            self._current()
            return record.model_dump(mode="json")

    def submit_review(self, payload: str) -> dict[str, Any]:
        with self._locked():
            self._current()
            if (
                self._phase != "analytical"
                or type(payload) is not str
                or len(payload.encode()) > MAX_LINE
            ):
                raise WorkflowError("not_permitted")
            key = (self._binding.ticket_id, self._binding.step_id, "submit_review")
            if self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            spec = self._spec
            # G1-X §3: a step whose inputs are not "none" (every session-less step, and a step
            # with pack sources that also has a view) is read on its own binding first.
            if spec.inputs != "none" and not any(r.binding == self._binding for r in self._reads):
                raise WorkflowError("not_permitted")
            evidence = (
                self._epoch_calls[-1].source_evidence if self._epoch_calls else SourceEvidence()
            )
            payload_bytes = payload.encode()
            binding = OwnerSubmissionBinding(
                binding=self._binding,
                payload_sha256=_hash(payload_bytes),
                call_ids=tuple(c.call_id for c in self._epoch_calls),
                successful_call_ids=tuple(c.call_id for c in self._epoch_calls if c.status == "ok"),
                source_evidence=evidence,
            )
            if (
                self._session is not None
                and _parse(OwnerSubmissionBinding, self._session.bind_submission(payload))
                != binding
            ):
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "payloads", binding.payload_sha256), payload_bytes)
            _retain(self._store, "bindings", binding)
            stored, resolved, paths, kinds = _fill(self._store, self._binding, payload)
            stored_hash = _hash(stored.encode())
            _put(_audit(self._store, "payloads", stored_hash), stored.encode())
            module_id = self._binding.module_id
            # G1-X §4: issues here refuse the submission: no journal step, no attempt consumed.
            issues = _gate(self._store, self._binding, spec, stored, evidence)
            rules = (
                (lambda text: _journaled_issues(module_id, spec.step_id, text, evidence))
                if spec.rules == "journaled"
                else None
            )
            self._current()
            attempt = None
            disposition: Literal["valid", "invalid", "refused"] = "refused"
            submitted_step = None
            if not issues:
                entry = self._specs[module_id].entry
                ticket_id = self._binding.ticket_id
                if entry == "cp0_review":
                    attempt = submit_cp0_review(self._store, ticket_id, stored)
                else:
                    # G1-X §2: an owner core journals its step and returns the same `Submitted`
                    # as `submit_model_payload`, so the identity check below holds for both.
                    submitted: Submitted = (
                        _CORES[module_id].submit(
                            self._store, ticket_id, spec.step_id, payload, rules
                        )
                        if entry == "owner_core"
                        else submit_model_payload(
                            self._store, ticket_id, spec.step_id, payload, rules=rules
                        )
                    )
                    if (
                        submitted.payload,
                        submitted.nulls_resolved,
                        submitted.prefilled,
                        submitted.prefilled_kinds,
                    ) != (stored, resolved, paths, kinds):
                        raise WorkflowError("identity_mismatch")
                    attempt = submitted.journal
                candidates = (
                    attempt.steps
                    if attempt.steps and attempt.steps[-1].step_id == spec.step_id
                    else attempt.step_repairs
                )
                if (
                    not candidates
                    or candidates[-1].payload_sha256 != stored_hash
                    or candidates[-1].step_id != spec.step_id
                ):
                    raise WorkflowError("identity_mismatch")
                submitted_step = candidates[-1]
                disposition = (
                    "valid"
                    if submitted_step.status == "valid" and not attempt.issues
                    else "invalid"
                )
                issues = submitted_step.issues or attempt.issues
            after = self._store.read()
            try:
                canonical = spec.schema.model_validate_json(stored).content_hash()
            except ValueError:
                canonical = None
            after_hash = after.content_hash()
            record = OwnerSubmission(
                sequence=len(self._submissions) + 1,
                binding=binding,
                stored_payload_sha256=stored_hash,
                canonical_review_sha256=canonical,
                disposition=disposition,
                issues=issues,
                snapshot_after_sha256=after_hash,
                nulls_resolved=resolved,
                prefilled=paths,
                prefilled_kinds=kinds,
                step_sha256=None if submitted_step is None else submitted_step.content_hash(),
                step_output_sha256=None if submitted_step is None else submitted_step.output_sha256,
            )
            _retain(self._store, "submissions", record)
            self._submissions.append(record)
            self._current_sha256 = after_hash
            if attempt is not None:
                chain = _sequence(module_id)
                if disposition == "valid" and attempt.status == "finished":
                    if len(attempt.steps) != len(chain):
                        raise WorkflowError("identity_mismatch")
                    self._advance(module_id)
                elif disposition == "valid":
                    self._activate(attempt, chain[len(attempt.steps)])
                elif attempt.status == "pending":
                    self._activate(attempt, spec.step_id)
                elif attempt.number == 0:
                    self._begin(module_id)
                else:
                    self._advance(module_id)  # attempt 1 settled blocked
            return {
                "schema_version": "financial-review-outcome/1",
                "status": disposition,
                "issues": list(issues),
                "step_id": spec.step_id,
                "refusal": self._refusal_code(),
                "snapshot_sha256": self._current_sha256,
                "next_step": self._binding.step_id if self._phase == "analytical" else None,
                "stored_payload_sha256": stored_hash,
                "prefilled": list(paths),
            }

    def _refusal_code(self) -> str | None:
        if not self._refusals:
            return None
        module = self._refusals[0].module_id.lower().replace("-", "")
        return f"{module}_{self._refusal_kind}"

    def publish(self) -> dict[str, Any]:
        with self._locked():
            before = self._current()
            publisher = next(
                (self._specs[m] for m in self._plan if self._specs[m].kind == "deterministic"),
                None,
            )
            if (
                self._phase != "walked"
                or len(self._publications) >= 2
                or publisher is None
                or publisher.publish is None
                or self._publication_directory is None
            ):
                raise WorkflowError("not_permitted")
            output = self._publication_directory
            ticket = None
            reason = None
            files: dict[str, str] = {}
            status: Literal["published", "refused", "failed"] = "refused"
            try:
                attempt = publisher.publish(self._store, output=output)
                ticket = attempt.ticket_id
                if verify_cp_model_publication(self._store, output):
                    raise WorkflowError("identity_mismatch")
                model = _record(self._store, publisher.module_id)
                files = _files(output)
                self._model = ModelPublication(
                    ticket_id=model.ticket_id,
                    result_sha256=model.result_sha256,
                    cp1_result_sha256=_record(self._store, "CP-1").result_sha256,
                    files=files,
                )
                status = "published"
                self._phase = "complete"
            except Exception as error:
                # Documented fail-closed: record why, finalize every owned partial publication.
                reason = str(error)
                known = {a.ticket_id for a in before.attempts}
                new = [a for a in self._store.read().attempts if a.ticket_id not in known]
                if new:
                    status = "failed"
                    ticket = new[0].ticket_id if len(new) == 1 else None
                    if len(new) != 1 or new[0].module_id != publisher.module_id:
                        self._phase = "failed"
                        raise WorkflowError("identity_mismatch") from error
                    if new[0].status == "pending":
                        try:
                            self._store.interrupt(
                                new[0].ticket_id, "Publication did not complete: " + reason
                            )
                        except Exception as cleanup_error:  # noqa: BLE001 - quarantine stays independent
                            reason += "; interruption failed: " + type(cleanup_error).__name__
                            self._phase = "failed"
                    if output.exists():
                        for name in FILES:
                            try:
                                path = output / name
                                if path.is_file():
                                    files[name] = _hash(path.read_bytes())
                            except OSError as hash_error:
                                reason += "; partial hash failed: " + type(hash_error).__name__
                        try:
                            output.rename(output.with_name(output.name + ".failed-" + str(uuid4())))
                        except OSError as quarantine_error:
                            reason += "; quarantine failed: " + type(quarantine_error).__name__
                            self._phase = "failed"
                    if any(h.module_id == publisher.module_id for h in self._store.read().heads):
                        self._phase = "failed"
                elif self._refused and isinstance(error, CpModelRefused):
                    self._phase = "complete"
            after = self._store.read()
            record = PublicationCall(
                snapshot_before_sha256=before.content_hash(),
                snapshot_after_sha256=after.content_hash(),
                status=status,
                reason=reason,
                ticket_id=ticket,
                files=files,
            )
            _retain(self._store, "publications", record)
            self._publications.append(record)
            self._current_sha256 = after.content_hash()
            return {
                "status": "ok" if status == "published" else "refused",
                "error_code": None
                if status == "published"
                else self._refusal_code() or "publication_refused",
                "snapshot_sha256": self._current_sha256,
            }

    def write_receipt(self, destination: Path) -> OwnerRunReceipt:
        with self._locked():
            snapshot = self._current()
            if self._phase != "complete":
                raise WorkflowError("not_permitted")
            receipt = OwnerRunReceipt(
                run=snapshot.run,
                pack_sha256=snapshot.pack_sha256,
                snapshot_sha256=snapshot.content_hash(),
                participant=self._participant,
                transport=self._transport,
                plan=self._plan,
                heads=tuple(_settled(self._store, h.module_id) for h in snapshot.heads),
                model=self._model,
                begins=tuple(self._begins),
                refusals=tuple(self._refusals),
                calls=tuple(self._calls),
                input_reads=tuple(self._reads),
                submissions=tuple(self._submissions),
                publications=tuple(self._publications),
            )
            _verify(
                self._store,
                receipt,
                publication_directory=self._publication_directory if self._model else None,
                sealed=False,
            )
            self._current()
            _put(self._store.directory / AUDIT / "receipt.sha256", receipt.content_hash().encode())
            _put(destination, receipt.model_dump_json().encode())
            self._current()
            self._sealed = True
            return receipt


def _verify_audit(store: Execution, receipt: OwnerRunReceipt) -> None:
    collections: dict[str, tuple[Contract, ...]] = {
        "calls": receipt.calls,
        "input-reads": receipt.input_reads,
        "submissions": receipt.submissions,
        "bindings": tuple(s.binding for s in receipt.submissions),
        "publications": receipt.publications,
        "begins": receipt.begins,
        "refused-begin": receipt.refusals,
    }
    for kind, values in collections.items():
        expected = {v.content_hash(): v.model_dump_json().encode() for v in values}
        directory = store.directory / AUDIT / kind
        actual = {p.name for p in directory.iterdir()} if directory.exists() else set()
        if actual != set(expected) or any(
            _audit(store, kind, digest).read_bytes() != raw for digest, raw in expected.items()
        ):
            raise WorkflowError("identity_mismatch")
    if len({c.call_id for c in receipt.calls}) != len(receipt.calls):
        raise WorkflowError("identity_mismatch")
    for records in (receipt.calls, receipt.input_reads):
        counts = Counter((r.binding.ticket_id, r.binding.step_id) for r in records)
        if any(count > MAX_CALLS for count in counts.values()):
            raise WorkflowError("identity_mismatch")
    sub_counts = Counter(
        (s.binding.binding.ticket_id, s.binding.binding.step_id) for s in receipt.submissions
    )
    if any(count > MAX_CALLS for count in sub_counts.values()):
        raise WorkflowError("identity_mismatch")


def _verify_begins(store: Execution, receipt: OwnerRunReceipt, analytical: frozenset[str]) -> None:
    """Each analytical attempt has exactly one retained begin that added exactly it."""
    snapshot = store.read()
    attempts = Counter(a.ticket_id for a in snapshot.attempts if a.module_id in analytical)
    if Counter(b.ticket_id for b in receipt.begins) != attempts:
        raise WorkflowError("identity_mismatch")
    for begin in receipt.begins:
        before = _snapshot(store, begin.snapshot_before_sha256)
        after = _snapshot(store, begin.snapshot_after_sha256)
        known = {a.ticket_id for a in before.attempts}
        added = [a for a in after.attempts if a.ticket_id not in known]
        if (
            len(added) != 1
            or (added[0].ticket_id, added[0].module_id, added[0].number)
            != (begin.ticket_id, begin.module_id, begin.attempt)
            or tuple(a for a in after.attempts if a.ticket_id != begin.ticket_id) != before.attempts
        ):
            raise WorkflowError("identity_mismatch")


def _verify_transition(
    before: ExecutionSnapshot,
    after: ExecutionSnapshot,
    kind: str,
    ticket_id: str | None,
    deterministic: str | None,
) -> None:
    """One recorded transition changes only what its operation may: a begin changes no head (its
    one added attempt is `_verify_begins`'); a submission changes only its ticket's attempt and
    that module's head; a publication only the deterministic module's head (its attempt is
    `_verify_publications`')."""
    if kind == "begin":
        if after.heads != before.heads:
            raise WorkflowError("identity_mismatch")
        return
    if kind == "publication":
        module_id = deterministic
    else:
        attempt = next((a for a in before.attempts if a.ticket_id == ticket_id), None)
        if (
            attempt is None
            or [a.ticket_id for a in after.attempts] != [a.ticket_id for a in before.attempts]
            or any(
                a != b
                for a, b in zip(after.attempts, before.attempts, strict=True)
                if a.ticket_id != ticket_id
            )
        ):
            raise WorkflowError("identity_mismatch")
        module_id = attempt.module_id
    if (
        tuple(h for h in after.heads if h.module_id != module_id)
        != tuple(h for h in before.heads if h.module_id != module_id)
        or sum(h.module_id == module_id for h in after.heads) > 1
    ):
        raise WorkflowError("identity_mismatch")


def _verify_chain(
    receipt: OwnerRunReceipt, chain: Sequence[ExecutionSnapshot], deterministic: str | None
) -> None:
    """R6-1: the recorded coordinates are one gapless chain from the created snapshot to the
    final one. Every begin, submission and publication is a transition `before -> after`;
    ordered along the ancestry, each starts where the previous one ended, the first at the root
    and the last at the final snapshot (so a refusal, bound to the final or the first
    publication's `before` by `_verify_walk`, sits at the walk's last `after`). Each transition
    passes `_verify_transition`. Within a ticket, the first submission is bound to its begin's
    `after` and each later one to the previous submission's `after`; every call and read is
    bound to one of those binding snapshots."""
    position = {snapshot.content_hash(): index for index, snapshot in enumerate(chain)}
    transitions: list[tuple[int, int, str, str | None]] = [
        (
            position[b.snapshot_before_sha256],
            position[b.snapshot_after_sha256],
            "begin",
            b.ticket_id,
        )
        for b in receipt.begins
    ]
    transitions += [
        (
            position[s.binding.binding.snapshot_sha256],
            position[s.snapshot_after_sha256],
            "submission",
            s.binding.binding.ticket_id,
        )
        for s in receipt.submissions
    ]
    transitions += [
        (
            position[p.snapshot_before_sha256],
            position[p.snapshot_after_sha256],
            "publication",
            p.ticket_id,
        )
        for p in receipt.publications
    ]
    transitions.sort(key=lambda item: item[:2])
    cursor = 0
    for before, after, kind, ticket_id in transitions:
        if before != cursor or after < before:
            raise WorkflowError("identity_mismatch")
        cursor = after
        _verify_transition(chain[before], chain[after], kind, ticket_id, deterministic)
    if cursor != len(chain) - 1:
        raise WorkflowError("identity_mismatch")
    expected = {b.ticket_id: b.snapshot_after_sha256 for b in receipt.begins}
    bindings: dict[str, set[str]] = {t: {digest} for t, digest in expected.items()}
    for submission in receipt.submissions:
        binding = submission.binding.binding
        if expected.get(binding.ticket_id) != binding.snapshot_sha256:
            raise WorkflowError("identity_mismatch")
        expected[binding.ticket_id] = submission.snapshot_after_sha256
        bindings[binding.ticket_id].add(binding.snapshot_sha256)
    bound = [c.binding for c in receipt.calls] + [r.binding for r in receipt.input_reads]
    for binding in bound:
        if binding.snapshot_sha256 not in bindings.get(binding.ticket_id, ()):
            raise WorkflowError("identity_mismatch")


def _verify_walk(store: Execution, receipt: OwnerRunReceipt, analytical: tuple[str, ...]) -> None:
    """Planned analytical modules are settled, or the first unsettled one was refused."""
    snapshot = store.read()
    heads = {h.module_id for h in snapshot.heads}
    refused = {r.module_id for r in receipt.refusals}
    if len(receipt.refusals) > 1 or len(heads) != len(snapshot.heads):
        raise WorkflowError("identity_mismatch")
    for index, module_id in enumerate(analytical):
        if module_id in heads:
            if module_id in refused:
                raise WorkflowError("identity_mismatch")
            continue
        if refused != {module_id}:
            raise WorkflowError("identity_mismatch")
        if any(a.module_id == module_id for a in snapshot.attempts) or any(
            m in heads for m in analytical[index + 1 :]
        ):
            raise WorkflowError("identity_mismatch")
        break
    else:
        if refused:
            raise WorkflowError("identity_mismatch")
    blocked = [
        m
        for m in analytical
        if any(h.module_id == m and h.status == "blocked" for h in snapshot.heads)
    ]
    if blocked and not receipt.refusals and analytical[-1] not in blocked:
        later = analytical[analytical.index(blocked[0]) + 1 :]
        if later and later[0] not in heads:
            raise WorkflowError("identity_mismatch")
    # The refusal ended the analytical walk. CP-MODEL may have published after it (H1), so the
    # snapshot it refused on is the one before the first publication, else the final one.
    refused_on = (
        receipt.publications[0].snapshot_before_sha256
        if receipt.publications
        else snapshot.content_hash()
    )
    for refusal in receipt.refusals:
        before = _snapshot(store, refusal.snapshot_sha256)
        if refusal.snapshot_sha256 != refused_on:
            raise WorkflowError("identity_mismatch")
        try:
            current_inputs(before, refusal.module_id)
        except NotAuthorized as error:
            if str(error) != refusal.reason:
                raise WorkflowError("identity_mismatch") from None
        except ValueError as error:
            if str(error) != refusal.reason or not str(error).startswith(BLOCKED_EDGE):
                raise WorkflowError("identity_mismatch") from None
        else:
            raise WorkflowError("identity_mismatch")


def _verify_publications(
    store: Execution, receipt: OwnerRunReceipt, terminal_refusal: bool, deterministic: str | None
) -> None:
    """Every begun publisher attempt and non-begin refusal has its retained transition."""
    snapshot = store.read()
    attempts = {a.ticket_id: a for a in snapshot.attempts if a.module_id == deterministic}
    recorded = Counter(p.ticket_id for p in receipt.publications if p.ticket_id is not None)
    if deterministic is None:
        if receipt.publications or receipt.model is not None:
            raise WorkflowError("identity_mismatch")
        return
    if recorded != Counter(attempts.keys()) or not 1 <= len(receipt.publications) <= 2:
        raise WorkflowError("identity_mismatch")
    previous_after = None
    for index, publication in enumerate(receipt.publications):
        before = _snapshot(store, publication.snapshot_before_sha256)
        after = _snapshot(store, publication.snapshot_after_sha256)
        if previous_after is not None and previous_after != publication.snapshot_before_sha256:
            raise WorkflowError("identity_mismatch")
        previous_after = publication.snapshot_after_sha256
        if publication.status == "refused":
            if (
                before != after
                or publication.ticket_id is not None
                or publication.files
                or not publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            if not terminal_refusal and not (
                publication.reason.startswith("Output ")
                and "already exists; publish into a new directory" in publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            continue
        known = {a.ticket_id for a in before.attempts}
        added = [a for a in after.attempts if a.ticket_id not in known]
        if (
            len(added) != 1
            or added[0].module_id != deterministic
            or added[0].ticket_id != publication.ticket_id
            or added[0] != attempts.get(publication.ticket_id)
            or tuple(a for a in after.attempts if a.ticket_id != publication.ticket_id)
            != before.attempts
            or set(publication.files) - set(FILES)
        ):
            raise WorkflowError("identity_mismatch")
        attempt = added[0]
        if publication.status == "published":
            if (
                index != len(receipt.publications) - 1
                or attempt.status != "finished"
                or attempt.issues
                or publication.reason is not None
                or receipt.model is None
                or publication.files != receipt.model.files
            ):
                raise WorkflowError("identity_mismatch")
        elif (
            attempt.status != "finished"
            or not attempt.issues
            or attempt.interruption is None
            or not publication.reason
        ):
            raise WorkflowError("identity_mismatch")


def _verify_calls_reads(
    store: Execution, receipt: OwnerRunReceipt, specs: Mapping[str, OwnerSpec]
) -> None:
    replayed: dict[str, SourceSession] = {}
    for call in receipt.calls:
        historical = _hist(store, call.binding)
        key = call.binding.content_hash()
        prior = [
            c for c in receipt.calls if c.binding == call.binding and c.sequence < call.sequence
        ]
        if call.sequence != len(prior) + 1 or call.sequence > MAX_CALLS:
            raise WorkflowError("identity_mismatch")
        if _step(specs, call.binding.module_id, call.binding.step_id).sources:
            if key not in replayed:
                replayed[key] = SourceSession.from_execution(
                    historical, call.binding.ticket_id, call.binding.step_id
                )
            expected = _parse(OwnerCall, replayed[key].invoke(call.tool, call.arguments))
            if expected.model_copy(update={"call_id": call.call_id}) != call:
                raise WorkflowError("identity_mismatch")
        elif (
            call.status != "refused"
            or call.error_code != "not_permitted"
            or call.body is not None
            or call.source_evidence != SourceEvidence()
        ):
            raise WorkflowError("identity_mismatch")
    for read in receipt.input_reads:
        read_spec = _step(specs, read.binding.module_id, read.binding.step_id)
        if read_spec.inputs == "none":
            raise WorkflowError("identity_mismatch")
        digest, body = _inputs(store, read.binding, read_spec)
        earlier = [
            r
            for r in receipt.input_reads
            if (r.binding.ticket_id, r.binding.step_id)
            == (read.binding.ticket_id, read.binding.step_id)
            and r.sequence < read.sequence
        ]
        if (
            (read.inputs_sha256, read.body) != (digest, body)
            or read.sequence != len(earlier) + 1
            or read.sequence > MAX_CALLS
        ):
            raise WorkflowError("identity_mismatch")


def _entry_outcome(
    historical: _FrozenExecution, binding: OwnerBinding, payload: str, attempt: Attempt
) -> StepValidation:
    """What the module's own entry validator says of `attempt` (its last step the one under
    replay) on the historical snapshot: `cp0_workflow._validate_review` for CP-0; for CP-1 the
    stage validator the pre-fill selects (`_validate_prefilled` when a marked field stays
    unset or unbound) or the promotion's `_quality_stage`; for any other module the validator
    registered in `_ENTRY_VALIDATORS` (the one its entry, or its owner core's `submit`, hands
    `Execution.submit_step`). A module without one is refused, never passed."""
    pack = historical.pack()
    module_id, step_id = binding.module_id, binding.step_id
    if module_id == "CP-0":
        return cp0_validate_review(historical, pack, attempt)
    if module_id == "CP-1":
        if step_id == "quality":
            return _quality_stage(historical, pack, attempt)[0]
        normal, _ = normalise(STEPS[step_id].schema, payload)
        known = known_bindings(historical, binding.ticket_id, step_id)
        filled = prefill(STEPS[step_id].schema, normal, known, PREFILLED[step_id])
        if filled.unbound or filled.unset:
            return _validate_prefilled(historical, known, step_id, pack, attempt)
        return validate_cp1_stage(historical, pack, attempt)
    validate = _ENTRY_VALIDATORS.get(module_id)
    if validate is None:
        raise WorkflowError("not_permitted")
    return validate(historical, pack, attempt)


def _unbounded_step_issues(
    spec: StepSpec, validator_issues: tuple[str, ...], journaled: tuple[str, ...]
) -> tuple[str, ...]:
    """The issues the core hands `settle` for an invalid step, before the journal's bound (rule
    issues arrive capped, 0d-c) (R4-1, R4-2): the entry validator's, with the journaled rule
    issues appended and de-duplicated exactly as `live.submission._with_rules` composes them (no
    dedupe when no rule found anything)."""
    if spec.rules == "journaled" and journaled:
        return tuple(dict.fromkeys((*validator_issues, *journaled)))
    return tuple(validator_issues)


def _verify_invalid_step(
    store: Execution,
    historical: _FrozenExecution,
    spec: StepSpec,
    binding: OwnerBinding,
    raw_payload: str,
    after: Attempt,
    step: StepSubmission,
    journaled: tuple[str, ...],
) -> Module | None:
    """Replay one invalid step as `Execution.submit_step` retained it (R4-1, R4-2, R5-3).

    The step's inputs are the attempt's plus one `step:` input per step completed before it;
    its output is the entry validator's replayed at the historical snapshot (hash and bytes) and
    its issues that validator's, bounded. A first rejection of a within-attempt-repair step
    leaves the attempt pending with the step in `step_repairs` (returns None); any other invalid
    step settles the attempt: the empty candidate, the `settle` of that candidate under the same
    issues, the finished attempt and the stored result must all be exactly what the core
    produces, and the rebuilt result is returned for the head check (R5-1)."""
    before = _attempt_of(historical.read(), binding.ticket_id)
    pending = step.model_copy(update={"status": "pending", "output_sha256": None, "issues": ()})
    view = before.model_copy(update={"steps": (*before.steps, pending)})
    outcome = _entry_outcome(historical, binding, raw_payload, view)
    unbounded = _unbounded_step_issues(spec, outcome.issues, journaled)
    inputs = (
        *before.inputs,
        *(Input(input_id="step:" + s.step_id, sha256=s.content_hash()) for s in before.steps),
    )
    if (
        step.status != "invalid"
        or not unbounded
        or step.issues != bounded_issues(unbounded)
        or step.inputs != inputs
        or not outcome.retained_as(step)
        or (
            outcome.output is not None
            and store.step_output(step.output_sha256 or "") != outcome.output
        )
    ):
        raise WorkflowError("identity_mismatch")
    repairable = binding.step_id in WITHIN_ATTEMPT_REPAIR.get(binding.module_id, frozenset())
    if repairable and all(item.step_id != binding.step_id for item in before.step_repairs):
        if after != before.model_copy(update={"step_repairs": (*before.step_repairs, step)}):
            raise WorkflowError("identity_mismatch")
        return None
    snapshot = historical.read()
    run = snapshot.run
    empty = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=binding.module_id,
        inputs=before.inputs,
        attempt=before.number,
    ).model_dump_json()
    submitted = before.model_copy(
        update={"steps": (*before.steps, step), "payload_sha256": text_sha256(empty)}
    )
    finished, result = settle(
        snapshot.model_copy(
            update={
                "parent": snapshot.content_hash(),
                "attempts": tuple(
                    view if a.ticket_id == binding.ticket_id else a for a in snapshot.attempts
                ),
            }
        ),
        submitted,
        empty,
        lambda _: unbounded,
        pack=historical.pack(),
        load=store.head_module,
    )
    if (
        finished != after
        or after.result_sha256 is None
        or store.payload(after.payload_sha256 or "") != empty
        or store.result(after.result_sha256) != result
    ):
        raise WorkflowError("identity_mismatch")
    return result


def _verify_attempts(
    snapshot: ExecutionSnapshot, receipt: OwnerRunReceipt, analytical: frozenset[str]
) -> None:
    """The repair chain of every analytical attempt (R4-1): attempt 0 repairs nothing; attempt 1
    repairs the finished, rejected attempt 0 of the same module and inputs, carrying its issues;
    a finished attempt with issues stopped on a recorded invalid step."""
    recorded = {(s.binding.binding.ticket_id, s.step_sha256) for s in receipt.submissions}
    seen: dict[str, Attempt] = {}
    repaired: set[str] = set()
    for attempt in (a for a in snapshot.attempts if a.module_id in analytical):
        if attempt.ticket_id in seen:
            raise WorkflowError("identity_mismatch")
        if attempt.number == 0:
            if attempt.repair_of is not None or attempt.repair_issues:
                raise WorkflowError("identity_mismatch")
        else:
            previous = seen.get(attempt.repair_of or "")
            if (
                previous is None
                or previous.ticket_id in repaired
                or previous.module_id != attempt.module_id
                or previous.number != 0
                or previous.status != "finished"
                or not previous.issues
                or previous.inputs != attempt.inputs
                or attempt.repair_issues != previous.issues
            ):
                raise WorkflowError("identity_mismatch")
            repaired.add(previous.ticket_id)
        if attempt.status == "finished" and attempt.issues:
            last = attempt.steps[-1] if attempt.steps else None
            if (
                last is None
                or last.status != "invalid"
                or attempt.interruption is not None
                or (attempt.ticket_id, last.content_hash()) not in recorded
            ):
                raise WorkflowError("identity_mismatch")
        seen[attempt.ticket_id] = attempt


@dataclass(frozen=True)
class _Settlement:
    """A finished attempt as the submission that settled it left it (R5-1): the attempt in that
    submission's `snapshot_after`, and the result its rebuilt invalid-step settlement produced
    (None when a valid step settled it; the module's probe re-settles that one)."""

    attempt: Attempt
    result: Module | None


def _verify_submissions(
    store: Execution, receipt: OwnerRunReceipt, specs: Mapping[str, OwnerSpec]
) -> tuple[list[tuple[str, str, str]], dict[str, _Settlement]]:
    """Replay every submission at its historical snapshot. Returns the valid steps and, per
    ticket, the settlement of each attempt a submission finished (at most one per ticket)."""
    valid: list[tuple[str, str, str]] = []
    settlements: dict[str, _Settlement] = {}
    for sequence, submission in enumerate(receipt.submissions, 1):
        if submission.sequence != sequence:
            raise WorkflowError("identity_mismatch")
        binding = submission.binding
        spec = _step(specs, binding.binding.module_id, binding.binding.step_id)
        # R4-3, G1-X §3: as at runtime, a step whose inputs are not "none" is read on its own
        # binding before its payload is filled or its gate runs.
        if spec.inputs != "none" and not any(
            r.binding == binding.binding for r in receipt.input_reads
        ):
            raise WorkflowError("identity_mismatch")
        historical = _hist(store, binding.binding)
        raw = _raw(store, binding.payload_sha256)
        filled, resolved, paths, kinds = _fill(historical, binding.binding, raw)
        if (filled, resolved, paths, kinds) != (
            _raw(store, submission.stored_payload_sha256),
            submission.nulls_resolved,
            submission.prefilled,
            submission.prefilled_kinds,
        ):
            raise WorkflowError("identity_mismatch")
        scoped = [c for c in receipt.calls if c.binding == binding.binding]
        prefix = scoped[: len(binding.call_ids)]
        evidence = prefix[-1].source_evidence if prefix else SourceEvidence()
        if (
            binding.call_ids != tuple(c.call_id for c in prefix)
            or binding.successful_call_ids != tuple(c.call_id for c in prefix if c.status == "ok")
            or binding.source_evidence != evidence
        ):
            raise WorkflowError("identity_mismatch")
        # G1-X §4: the gate is recomputed for every submission. A refused record must reproduce
        # exactly its issues; a journaled (valid or invalid) step must yield none.
        issues = _gate(historical, binding.binding, spec, filled, evidence)
        after = _snapshot(store, submission.snapshot_after_sha256)
        if after.run != receipt.run or after.pack_sha256 != receipt.pack_sha256:
            raise WorkflowError("identity_mismatch")
        try:
            canonical: str | None = spec.schema.model_validate_json(filled).content_hash()
        except ValueError:
            canonical = None
        if canonical != submission.canonical_review_sha256:
            raise WorkflowError("identity_mismatch")
        if submission.disposition == "refused":
            if (
                not issues
                or submission.issues != issues
                or after.content_hash() != binding.binding.snapshot_sha256
                or submission.step_sha256 is not None
                or submission.step_output_sha256 is not None
            ):
                raise WorkflowError("identity_mismatch")
            continue
        if issues:
            raise WorkflowError("identity_mismatch")
        # The journaled rules (`ToolRules`, or the owner core's `RULES`) at the same evidence.
        journaled = (
            _journaled_issues(binding.binding.module_id, spec.step_id, filled, evidence)
            if spec.rules == "journaled"
            else ()
        )
        attempt = _attempt_of(after, binding.binding.ticket_id)
        before_attempt = _attempt_of(historical.read(), binding.binding.ticket_id)
        candidates = (
            attempt.steps
            if len(attempt.steps) > len(before_attempt.steps)
            else attempt.step_repairs[len(before_attempt.step_repairs) :]
        )
        matches = [s for s in candidates[-1:] if s.content_hash() == submission.step_sha256]
        if (
            len(matches) != 1
            or matches[0].payload_sha256 != submission.stored_payload_sha256
            or matches[0].output_sha256 != submission.step_output_sha256
        ):
            raise WorkflowError("identity_mismatch")
        step = matches[0]
        result: Module | None = None
        if submission.disposition == "valid":
            if step.status != "valid" or submission.issues or journaled:
                raise WorkflowError("identity_mismatch")
            valid.append((attempt.ticket_id, step.step_id, step.content_hash()))
            settled = attempt.status == "finished"
        else:
            if step.issues != submission.issues:
                raise WorkflowError("identity_mismatch")
            result = _verify_invalid_step(
                store,
                historical,
                spec,
                binding.binding,
                _raw(store, binding.payload_sha256),
                attempt,
                step,
                journaled,
            )
            settled = result is not None
        if settled:
            if attempt.ticket_id in settlements:
                raise WorkflowError("identity_mismatch")
            settlements[attempt.ticket_id] = _Settlement(attempt, result)
    return valid, settlements


def _verify_settlements(
    store: Execution,
    snapshot: ExecutionSnapshot,
    settlements: Mapping[str, _Settlement],
    analytical: tuple[str, ...],
) -> list[tuple[str, str, str]]:
    """R5-1: the final snapshot holds every finished analytical attempt exactly as the submission
    that settled it left it, and no other finished one. Every analytical head is such an
    attempt's result: a blocked head is the rebuilt invalid-step settlement of attempt 1 (issues,
    an invalid last step); any other head is a valid settlement its module's probe re-settles on
    the final snapshot, and no valid settlement sits outside a head. Every analytical head's
    attempt was begun on the inputs the final snapshot binds for its module (R6-1). Returns the
    steps of every probed head attempt; each needs a valid submission."""
    finished = {
        a.ticket_id: a
        for a in snapshot.attempts
        if a.module_id in analytical and a.status == "finished"
    }
    if set(finished) != set(settlements) or any(
        finished[ticket] != settlement.attempt for ticket, settlement in settlements.items()
    ):
        raise WorkflowError("identity_mismatch")
    probed: set[str] = set()
    expected: list[tuple[str, str, str]] = []
    for head in snapshot.heads:
        if head.module_id not in analytical:
            continue
        attempt = _result_attempt(snapshot, head)
        settlement = settlements.get(attempt.ticket_id)
        if settlement is None:
            raise WorkflowError("identity_mismatch")
        # R6-1: the head's attempt was begun on exactly the inputs the final snapshot binds for
        # its module. A CP-0 head that no longer commands this consumer (NotAuthorized) or an
        # upstream the final snapshot does not bind (any other ValueError) is a forgery, not a
        # pass: both map to identity_mismatch explicitly.
        try:
            bound = current_inputs(snapshot, head.module_id)
        except NotAuthorized:
            raise WorkflowError("identity_mismatch") from None
        except ValueError:
            raise WorkflowError("identity_mismatch") from None
        if bound != attempt.inputs:
            raise WorkflowError("identity_mismatch")
        if head.status == "blocked":
            if (
                settlement.result is None
                or attempt.number != 1
                or not attempt.issues
                or not attempt.steps
                or attempt.steps[-1].status != "invalid"
                or head != head_of(settlement.result)
            ):
                raise WorkflowError("identity_mismatch")
            continue
        if settlement.result is not None or attempt.issues:
            raise WorkflowError("identity_mismatch")
        _PROBES[head.module_id](store, snapshot, attempt)
        probed.add(attempt.ticket_id)
        expected += [(attempt.ticket_id, s.step_id, s.content_hash()) for s in attempt.steps]
    if any(s.result is None and ticket not in probed for ticket, s in settlements.items()):
        raise WorkflowError("identity_mismatch")
    return expected


def _verify(
    store: Execution,
    receipt: OwnerRunReceipt,
    *,
    publication_directory: Path | None,
    sealed: bool,
) -> None:
    snapshot = store.read()
    if (snapshot.run, snapshot.pack_sha256, snapshot.content_hash()) != (
        receipt.run,
        receipt.pack_sha256,
        receipt.snapshot_sha256,
    ):
        raise WorkflowError("stale_binding")
    store.pack(snapshot)
    planned = plan(snapshot.run.requested_modules)
    # A run `create` could not have opened (a planned module without a spec) is evidence that
    # does not bind (R4-4), not a raw lookup failure.
    if receipt.plan != planned or any(m not in OWNER_SPECS for m in planned):
        raise WorkflowError("identity_mismatch")
    analytical = tuple(m for m in planned if OWNER_SPECS[m].kind == "analytical")
    deterministic = next((m for m in planned if OWNER_SPECS[m].kind == "deterministic"), None)
    if len(receipt.heads) != len(snapshot.heads) or {h.module_id for h in snapshot.heads} != {
        h.module_id for h in receipt.heads
    }:
        raise WorkflowError("identity_mismatch")
    for head in snapshot.heads:
        if head != head_of(store.head_module(head), _QUALIFICATION.get(head.module_id)):
            raise WorkflowError("identity_mismatch")
        if _settled(store, head.module_id) not in receipt.heads:
            raise WorkflowError("identity_mismatch")
    retained = Counter(
        (a.ticket_id, s.content_hash())
        for a in snapshot.attempts
        if a.module_id in analytical
        for s in (*a.steps, *a.step_repairs)
    )
    recorded = Counter(
        (s.binding.binding.ticket_id, s.step_sha256)
        for s in receipt.submissions
        if s.disposition != "refused"
    )
    if retained != recorded:
        raise WorkflowError("identity_mismatch")
    # R6-2: every attempt and head in every snapshot of the run is a planned module, and the only
    # non-analytical one is the planned deterministic module.
    allowed = frozenset(analytical) | frozenset(() if deterministic is None else (deterministic,))
    ancestors = set()
    chain: list[ExecutionSnapshot] = []
    cursor = snapshot
    while True:
        digest = cursor.content_hash()
        if (
            digest in ancestors
            or cursor.run != receipt.run
            or cursor.pack_sha256 != receipt.pack_sha256
            or any(a.module_id not in allowed for a in cursor.attempts)
            or any(h.module_id not in allowed for h in cursor.heads)
        ):
            raise WorkflowError("identity_mismatch")
        ancestors.add(digest)
        chain.append(cursor)
        if cursor.parent is None:
            break
        cursor = _snapshot(store, cursor.parent)
    chain.reverse()
    bindings = (
        [c.binding for c in receipt.calls]
        + [r.binding for r in receipt.input_reads]
        + [s.binding.binding for s in receipt.submissions]
    )
    coordinates = [b.snapshot_sha256 for b in bindings]
    coordinates += [s.snapshot_after_sha256 for s in receipt.submissions]
    coordinates += [r.snapshot_sha256 for r in receipt.refusals]
    coordinates += [
        x for b in receipt.begins for x in (b.snapshot_before_sha256, b.snapshot_after_sha256)
    ]
    coordinates += [
        x for p in receipt.publications for x in (p.snapshot_before_sha256, p.snapshot_after_sha256)
    ]
    if any(digest not in ancestors for digest in coordinates):
        raise WorkflowError("identity_mismatch")
    if (
        sealed
        and (store.directory / AUDIT / "receipt.sha256").read_text() != receipt.content_hash()
    ):
        raise WorkflowError("identity_mismatch")
    _verify_audit(store, receipt)
    _verify_begins(store, receipt, frozenset(analytical))
    _verify_attempts(snapshot, receipt, frozenset(analytical))
    _verify_walk(store, receipt, analytical)
    terminal = deterministic is not None and _terminal(snapshot.heads, snapshot.run, deterministic)
    _verify_publications(store, receipt, terminal, deterministic)
    _verify_chain(receipt, chain, deterministic)
    _verify_calls_reads(store, receipt, OWNER_SPECS)
    valid, settlements = _verify_submissions(store, receipt, OWNER_SPECS)
    expected_steps = _verify_settlements(store, snapshot, settlements, analytical)
    if not all(item in valid for item in expected_steps):
        raise WorkflowError("identity_mismatch")
    _verify_publication_outcome(
        store, snapshot, receipt, publication_directory, terminal, deterministic
    )
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise WorkflowError("stale_binding")


def _verify_publication_outcome(
    store: Execution,
    snapshot: ExecutionSnapshot,
    receipt: OwnerRunReceipt,
    directory: Path | None,
    terminal: bool,
    deterministic: str | None,
) -> None:
    if deterministic is None:
        if directory is not None:
            raise WorkflowError("identity_mismatch")
        return
    if receipt.model is None:
        publication = receipt.publications[0] if len(receipt.publications) == 1 else None
        if (
            not terminal
            or directory is not None
            or publication is None
            or any(a.module_id == deterministic for a in snapshot.attempts)
            or any(h.module_id == deterministic for h in snapshot.heads)
        ):
            raise WorkflowError("identity_mismatch")
        with tempfile.TemporaryDirectory() as refused_directory:
            try:
                publish_cp_model(
                    _FrozenExecution(store, snapshot), output=Path(refused_directory) / "absent"
                )
            except CpModelRefused as error:
                expected = PublicationCall(
                    snapshot_before_sha256=snapshot.content_hash(),
                    snapshot_after_sha256=snapshot.content_hash(),
                    status="refused",
                    reason=str(error),
                    ticket_id=None,
                    files={},
                )
                if publication != expected:
                    raise WorkflowError("identity_mismatch") from None
            else:
                raise WorkflowError("identity_mismatch")
        return
    # R4-4: a recorded publication without the heads it names is a tamper cause, checked here
    # before `financial_workflow._record` looks them up.
    if not {deterministic, "CP-1"} <= {h.module_id for h in snapshot.heads}:
        raise WorkflowError("identity_mismatch")
    model = _record(store, deterministic)
    if (
        terminal
        or directory is None
        or set(receipt.model.files) != set(FILES)
        or _files(directory) != receipt.model.files
        or (model.ticket_id, model.result_sha256, _record(store, "CP-1").result_sha256)
        != (receipt.model.ticket_id, receipt.model.result_sha256, receipt.model.cp1_result_sha256)
        or verify_cp_model_publication(store, directory)
    ):
        raise WorkflowError("identity_mismatch")
    _verify_model_settlement(store, snapshot, directory)
    last = receipt.publications[-1]
    if (
        last.status != "published"
        or last.ticket_id != model.ticket_id
        or last.files != receipt.model.files
        or last.snapshot_after_sha256 != snapshot.content_hash()
    ):
        raise WorkflowError("identity_mismatch")


def verify_owner_run_receipt(
    store: Execution, receipt: OwnerRunReceipt, *, publication_directory: Path | None = None
) -> None:
    """Authenticate sealed participation evidence read-only. Every submission is replayed at its
    historical snapshot (R4-2), every settlement rebuilt and bound to the final snapshot (R5-1),
    the recorded coordinates form one gapless chain of own-ticket transitions from the created
    snapshot to the final one and every head binds the final snapshot's inputs (R6-1), and only
    planned modules appear anywhere in it (R6-2); nothing is written.

    Exception mapping (S1a R4-4, as B1 N2): a tamper cause refuses `identity_mismatch`. Those are
    evidence that fails to parse or to hash (`ValueError`: pydantic, JSON, UTF-8, the store's
    blob and snapshot checks, the core refusals) and evidence that is missing or unreadable
    (`OSError`); every lookup a forged record can reach is an explicit check. Programming errors
    (`TypeError`, `KeyError`, `StopIteration`, `AttributeError`, ...) propagate unchanged."""
    try:
        receipt = OwnerRunReceipt.model_validate_json(receipt.model_dump_json())
        _verify(store, receipt, publication_directory=publication_directory, sealed=True)
    except WorkflowError:
        raise
    except (ValueError, OSError):
        raise WorkflowError("identity_mismatch") from None


def serve_json_lines(
    workflow: OwnerWorkflow,
    reader: TextIO,
    writer: TextIO,
    *,
    destination: Path,
    participant: str,
) -> None:
    if workflow._calls or workflow._submissions or workflow._reads:
        raise WorkflowError("not_permitted")
    workflow._participant, workflow._transport = participant, "bounded-json-lines/1"
    for _ in range(MAX_MESSAGES):
        line = reader.readline(MAX_LINE + 1)
        if not line:
            return
        try:
            if len(line) > MAX_LINE or not line.endswith("\n"):
                while line and not line.endswith("\n"):
                    line = reader.readline(MAX_LINE + 1)
                raise WorkflowError("bad_arguments")
            request = json.loads(line, parse_constant=_nonfinite_json)
            if type(request) is not dict:
                raise WorkflowError("bad_arguments")
            operation = request.get("operation")
            if operation == "invoke" and set(request) == {"operation", "tool", "arguments"}:
                result = workflow.invoke(request["tool"], request["arguments"])
            elif operation == "submit_review" and set(request) == {"operation", "payload"}:
                result = workflow.submit_review(request["payload"])
            elif operation == "read_inputs" and set(request) == {"operation"}:
                result = workflow.read_inputs()
            elif operation == "publish" and set(request) == {"operation"}:
                result = workflow.publish()
            elif operation == "write_receipt" and set(request) == {"operation"}:
                receipt = workflow.write_receipt(destination)
                result = {
                    "status": "ok",
                    "receipt_sha256": receipt.content_hash(),
                    "snapshot_sha256": receipt.snapshot_sha256,
                }
            else:
                raise WorkflowError("not_permitted")
        except (WorkflowError, SourceError) as error:
            result = {"status": "refused", "error_code": error.code}
        except (ValueError, TypeError, KeyError, UnicodeError):
            result = {"status": "refused", "error_code": "bad_arguments"}
        except Exception:  # noqa: BLE001 - sanitized bounded analytical transport (as the financial slice)
            result = {"status": "error", "error_code": "internal_error"}
        writer.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
        writer.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded offline owner workflow")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--publication-directory", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--participant", required=True)
    args = parser.parse_args()
    pack = PreparedPack.model_validate_json(args.pack.read_bytes())
    workflow = OwnerWorkflow.create(
        args.directory, pack, publication_directory=args.publication_directory
    )
    serve_json_lines(
        workflow, sys.stdin, sys.stdout, destination=args.receipt, participant=args.participant
    )


if __name__ == "__main__":
    main()
