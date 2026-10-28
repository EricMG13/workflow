"""Plan-driven offline owner workflow: one adapter for every declared owner spec.

Execution and the adopted owner cores own every calculation and settlement. This
adapter owns finite capabilities, immutable participation evidence and the receipt.
It generalises `financial_workflow` (which stays the reference and is imported, never
edited): the walk follows `registry.plan`, each module's steps come from a declared
`OwnerSpec`, and paths are supplied by trusted setup, never by a message.
G1 ships CP-0, CP-1 and CP-MODEL; no durable resume exists (an interrupted run is
refused and a new run starts).
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from types import MappingProxyType
from typing import Any, Literal, TextIO
from uuid import uuid4

from deploy_vii.contracts import Contract, Hash, Identifier, Input, Run
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.cp1_workflow import PROMOTED
from deploy_vii.cp_model_workflow import (
    PUBLISHED,
    CpModelRefused,
    publish_cp_model,
    verify_cp_model_publication,
)
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    NotAuthorized,
    current_inputs,
    head_of,
)
from deploy_vii.live.submission import submit_model_payload
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import plan, step_chain
from deploy_workflow.financial_workflow import (
    FILES,
    MAX_CALLS,
    MAX_LINE,
    MAX_MESSAGES,
    FinancialBinding,
    ModelPublication,
    PublicationCall,
    _binding,
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
from deploy_workflow.tools.source import SourceError
from deploy_workflow.workflow import SourceEvidence, WorkflowError

AUDIT = "owner-run-audit"
SUPPORTED_ANALYTICAL = frozenset({"CP-0", "CP-1"})  # the reused helpers are bound to these
ENTRIES = ("cp0_review", "model_payload")
BLOCKED_EDGE = "Required upstream is unrun, stale or blocked"
_QUALIFICATION = {"CP-1": PROMOTED, "CP-MODEL": PUBLISHED}
_PROBES: dict[str, Callable[[Execution, ExecutionSnapshot, Attempt], None]] = {
    "CP-0": _verify_cp0,
    "CP-1": _verify_promotion,
}


@dataclass(frozen=True)
class StepSpec:
    """One journal step. `sources`: pack tools (SourceSession); `extract`: statement
    extraction is offered; `upstream_grant`: frozen-upstream grant (none in G1);
    `inputs`: `projection` lets `read_inputs` return the adopted view; `rules`: the
    evidence rules of `financial_workflow._evidence_issues` apply to the payload."""

    step_id: str
    schema: type[Contract]
    sources: bool
    extract: bool
    upstream_grant: Mapping[str, Any] | None
    inputs: Literal["none", "projection"]
    rules: bool


@dataclass(frozen=True)
class OwnerSpec:
    module_id: str
    steps: tuple[StepSpec, ...]
    entry: Literal["cp0_review", "model_payload"] | None
    kind: Literal["analytical", "deterministic"]
    publish: Callable[..., Attempt] | None


def _default_specs() -> dict[str, OwnerSpec]:
    from deploy_vii.cp1_workflow import FinancialSubmission
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
        inputs: Literal["none", "projection"] = "none",
        rules: bool = False,
    ) -> StepSpec:
        return StepSpec(step_id, schema, sources, extract, None, inputs, rules)

    return {
        "CP-0": OwnerSpec(
            "CP-0",
            (step("source_readiness", ReadinessReview, sources=True, rules=True),),
            "cp0_review",
            "analytical",
            None,
        ),
        "CP-1": OwnerSpec(
            "CP-1",
            (
                step("source_context", SourceContextReview, sources=True, rules=True),
                step("financials", FinancialSubmission, sources=True, extract=True, rules=True),
                step("narrative", NarrativeReview, inputs="projection"),
                step("readiness", DownstreamReview, inputs="projection"),
                step("quality", QualityReview, inputs="projection"),
            ),
            "model_payload",
            "analytical",
            None,
        ),
        "CP-MODEL": OwnerSpec("CP-MODEL", (), None, "deterministic", publish_cp_model),
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
    return OwnerBinding.model_validate(_binding(snapshot, attempt, step_id).model_dump())


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
    head = next(h for h in snapshot.heads if h.module_id == module_id)
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
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
    return next(s for s in specs[module_id].steps if s.step_id == step_id)


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
        try:
            chain = step_chain(module_id)
        except ValueError:
            raise WorkflowError("not_permitted") from None
        if spec.entry not in ENTRIES or tuple(s.step_id for s in spec.steps) != chain.steps:
            raise WorkflowError("not_permitted")
        for item in spec.steps:
            if (
                item.upstream_grant is not None  # grant calls are not verifiable in G1
                or item.sources != (item.step_id in chain.pack_sources)
                or item.extract != (item.step_id in chain.extract_tools)
                or (not item.sources and item.inputs == "none")
            ):
                raise WorkflowError("not_permitted")
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
        return bool(self._refusals) or any(h.status == "blocked" for h in self._store.read().heads)

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
        _historical(self._store, _fin(self._binding))

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
                or self._spec.inputs != "projection"
                or self._limits[key] >= MAX_CALLS
            ):
                raise WorkflowError("not_permitted")
            digest, body = _projection(self._store, _fin(self._binding))
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
            spec, fin = self._spec, _fin(self._binding)
            if self._session is None and not any(r.binding == self._binding for r in self._reads):
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
            stored, resolved, paths, kinds = _filled(self._store, fin, payload)
            stored_hash = _hash(stored.encode())
            _put(_audit(self._store, "payloads", stored_hash), stored.encode())
            issues = _evidence_issues(self._store, fin, stored, evidence) if spec.rules else ()
            self._current()
            attempt = None
            disposition: Literal["valid", "invalid", "refused"] = "refused"
            submitted_step = None
            if not issues:
                if spec.step_id == "source_readiness" and self._binding.module_id == "CP-0":
                    attempt = submit_cp0_review(self._store, self._binding.ticket_id, stored)
                else:
                    submitted = submit_model_payload(
                        self._store, self._binding.ticket_id, spec.step_id, payload
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
            module_id = self._binding.module_id
            if attempt is not None:
                chain = step_chain(module_id).steps
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
    for refusal in receipt.refusals:
        before = _snapshot(store, refusal.snapshot_sha256)
        if refusal.snapshot_sha256 != snapshot.content_hash():
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
        historical = _historical(store, _fin(call.binding))
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
        if _step(specs, read.binding.module_id, read.binding.step_id).inputs != "projection":
            raise WorkflowError("identity_mismatch")
        digest, body = _projection(store, _fin(read.binding))
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


def _verify_submissions(
    store: Execution, receipt: OwnerRunReceipt, specs: Mapping[str, OwnerSpec]
) -> list[tuple[str, str, str]]:
    valid: list[tuple[str, str, str]] = []
    for sequence, submission in enumerate(receipt.submissions, 1):
        if submission.sequence != sequence:
            raise WorkflowError("identity_mismatch")
        binding = submission.binding
        spec = _step(specs, binding.binding.module_id, binding.binding.step_id)
        fin = _fin(binding.binding)
        historical = _historical(store, fin)
        filled, resolved, paths, kinds = _filled(
            historical, fin, _raw(store, binding.payload_sha256)
        )
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
        issues = _evidence_issues(historical, fin, filled, evidence) if spec.rules else ()
        after = _snapshot(store, submission.snapshot_after_sha256)
        if after.run != receipt.run or after.pack_sha256 != receipt.pack_sha256:
            raise WorkflowError("identity_mismatch")
        if submission.disposition == "refused":
            if (
                not issues
                or submission.issues != issues
                or after.content_hash() != binding.binding.snapshot_sha256
                or submission.step_sha256 is not None
            ):
                raise WorkflowError("identity_mismatch")
            continue
        if issues:
            raise WorkflowError("identity_mismatch")
        try:
            canonical: str | None = spec.schema.model_validate_json(filled).content_hash()
        except ValueError:
            canonical = None
        if canonical != submission.canonical_review_sha256:
            raise WorkflowError("identity_mismatch")
        attempt = next(a for a in after.attempts if a.ticket_id == binding.binding.ticket_id)
        before_attempt = next(
            a for a in historical.read().attempts if a.ticket_id == binding.binding.ticket_id
        )
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
        if submission.disposition == "valid":
            if step.status != "valid" or submission.issues:
                raise WorkflowError("identity_mismatch")
            valid.append((attempt.ticket_id, step.step_id, step.content_hash()))
            if not spec.sources and not any(
                r.binding == binding.binding for r in receipt.input_reads
            ):
                raise WorkflowError("identity_mismatch")
        elif step.status != "invalid" or step.issues != submission.issues:
            raise WorkflowError("identity_mismatch")
    return valid


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
    if receipt.plan != planned:
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
    ancestors = set()
    cursor = snapshot
    while True:
        digest = cursor.content_hash()
        if (
            digest in ancestors
            or cursor.run != receipt.run
            or cursor.pack_sha256 != receipt.pack_sha256
        ):
            raise WorkflowError("identity_mismatch")
        ancestors.add(digest)
        if cursor.parent is None:
            break
        cursor = _snapshot(store, cursor.parent)
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
    _verify_walk(store, receipt, analytical)
    terminal = bool(receipt.refusals) or any(h.status == "blocked" for h in snapshot.heads)
    _verify_publications(store, receipt, terminal, deterministic)
    _verify_calls_reads(store, receipt, OWNER_SPECS)
    valid = _verify_submissions(store, receipt, OWNER_SPECS)
    expected_steps: list[tuple[str, str, str]] = []
    for head in snapshot.heads:
        if head.module_id not in analytical or head.status == "blocked":
            continue
        attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
        _PROBES[head.module_id](store, snapshot, attempt)
        expected_steps += [(attempt.ticket_id, s.step_id, s.content_hash()) for s in attempt.steps]
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
    """Authenticate sealed participation evidence read-only; submissions are not replayed."""
    try:
        receipt = OwnerRunReceipt.model_validate_json(receipt.model_dump_json())
        _verify(store, receipt, publication_directory=publication_directory, sealed=True)
    except WorkflowError:
        raise
    except (ValueError, OSError, KeyError, StopIteration, TypeError, UnicodeError):
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
