"""Bounded offline CP-1 participation, verified promotion and deterministic publication.

Execution and the adopted financial core own every calculation and settlement.
This adapter owns finite capabilities, immutable participation evidence and the
final C1 -> C2 receipt. Paths are supplied by trusted setup, never by a message.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Literal, TextIO
from uuid import uuid4

from pydantic import BaseModel

from deploy_vii.contracts import Contract, Hash, Identifier, Input, Run
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.cp1_quality import cp1_quality_inputs
from deploy_vii.cp1_workflow import (
    CP1_PROMOTION,
    PROMOTED,
    CP1Handoff,
    FinancialStage,
    FinancialSubmission,
    cp1_registers,
    promote_cp1,
    read_cp1_envelope,
    validate_cp1_stage,
    write_cp1_envelope,
)
from deploy_vii.cp_model_workflow import (
    PUBLISHED,
    CpModelRefused,
    publish_cp_model,
    verify_cp_model_publication,
)
from deploy_vii.downstream_readiness import DownstreamInputs, DownstreamReview
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    NotAuthorized,
    current_inputs,
)
from deploy_vii.live.context import narrative_evidence, readiness_inputs
from deploy_vii.live.schema import normalise
from deploy_vii.live.submission import (
    PREFILLED,
    STEPS,
    known_bindings,
    prefill,
    submit_model_payload,
)
from deploy_vii.live.tools import PackTools, ToolRules, seen_tables
from deploy_vii.narrative import NarrativeReview
from deploy_vii.preparation import PreparedPack
from deploy_vii.quality import QualityReview, assess_quality
from deploy_vii.readiness import ReadinessReview
from deploy_vii.source_context import SourceContextReview
from deploy_workflow.host import SourceSession
from deploy_workflow.tools.source import SourceError
from deploy_workflow.workflow import SourceEvidence, WorkflowError

Step = Literal[
    "source_readiness", "source_context", "financials", "narrative", "readiness", "quality"
]
SOURCE_STEPS = ("source_readiness", "source_context", "financials")
FILES = ("model.html", "calculation.json", "receipt.json")
MAX_CALLS = 16
MAX_MESSAGES = 128
MAX_LINE = 4 * 1024 * 1024
# A located statement page holds a whole line that is a statement heading: the synthetic
# "[CONSOLIDATED] INCOME STATEMENT | CASH FLOW STATEMENT | BALANCE SHEET" and the filed SEC
# "CONSOLIDATED [CONDENSED] BALANCE SHEETS | STATEMENTS OF OPERATIONS | STATEMENTS OF CASH FLOWS".
# Comprehensive income and stockholders' equity statements are not located statements.
STATEMENT_HEADING = re.compile(
    r"^\s*(?:CONSOLIDATED\s+)?(?:CONDENSED\s+)?"
    r"(?:INCOME STATEMENT|CASH FLOW STATEMENT|BALANCE SHEETS?"
    r"|STATEMENTS OF OPERATIONS|STATEMENTS OF CASH FLOWS)\s*$",
    re.M,
)
SCHEMAS: dict[str, type[Contract]] = {
    "source_readiness": ReadinessReview,
    "source_context": SourceContextReview,
    "financials": FinancialSubmission,
    "narrative": NarrativeReview,
    "readiness": DownstreamReview,
    "quality": QualityReview,
}


class FinancialBinding(Contract):
    run_id: Identifier
    issuer_id: Identifier
    as_of: str
    method_version: str
    pack_sha256: Hash
    snapshot_sha256: Hash
    module_id: Literal["CP-0", "CP-1"]
    step_id: Step
    ticket_id: Identifier
    attempt: int
    inputs: tuple[Input, ...]


class FinancialCall(Contract):
    schema_version: Literal["tool-receipt/1"]
    call_id: str
    sequence: int
    binding: FinancialBinding
    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "refused", "error"]
    body: str | None
    error_code: str | None
    source_evidence: SourceEvidence


class InputRead(Contract):
    binding: FinancialBinding
    sequence: int
    operation: Literal["read_inputs"] = "read_inputs"
    inputs_sha256: Hash
    body: str


class FinancialSubmissionBinding(Contract):
    schema_version: Literal["submission-binding/1"] = "submission-binding/1"
    binding: FinancialBinding
    payload_sha256: Hash
    successful_call_ids: tuple[str, ...]
    call_ids: tuple[str, ...]
    source_evidence: SourceEvidence


class StageSubmission(Contract):
    sequence: int
    binding: FinancialSubmissionBinding
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


class PromotedRecord(Contract):
    ticket_id: Identifier
    result_sha256: Hash
    status: Literal["accepted", "restricted"]


class ModelPublication(Contract):
    ticket_id: Identifier
    result_sha256: Hash
    cp1_result_sha256: Hash
    files: dict[str, Hash]


class RefusedBegin(Contract):
    snapshot_sha256: Hash
    operation: Literal["begin_cp1"] = "begin_cp1"
    reason: str


class PublicationCall(Contract):
    snapshot_before_sha256: Hash
    snapshot_after_sha256: Hash
    status: Literal["published", "refused", "failed"]
    reason: str | None
    ticket_id: Identifier | None
    files: dict[str, Hash]


class FinancialSliceReceipt(Contract):
    schema_version: Literal["cp1-model-slice-receipt/1"] = "cp1-model-slice-receipt/1"
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    participant: str
    transport: Literal["python-api", "bounded-json-lines/1"]
    cp0: PromotedRecord
    cp1: PromotedRecord | None
    model: ModelPublication | None
    refusal: Literal["cp1_not_authorized"] | None
    calls: tuple[FinancialCall, ...]
    input_reads: tuple[InputRead, ...]
    submissions: tuple[StageSubmission, ...]
    refused_begin: RefusedBegin | None
    publications: tuple[PublicationCall, ...]


def _parse[T: BaseModel](model: type[T], value: Any) -> T:
    return model.model_validate_json(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _put(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise WorkflowError("identity_mismatch") from None


def _audit(store: Execution, kind: str, digest: str) -> Path:
    return store.directory / "financial-slice-audit" / kind / digest


def _retain(store: Execution, kind: str, value: Contract) -> None:
    _put(_audit(store, kind, value.content_hash()), value.model_dump_json().encode())


def _raw(store: Execution, digest: str) -> str:
    raw = _audit(store, "payloads", digest).read_bytes()
    if _hash(raw) != digest:
        raise WorkflowError("identity_mismatch")
    return raw.decode("utf-8")


def _snapshot(store: Execution, digest: str) -> ExecutionSnapshot:
    raw = (store.directory / "snapshots" / (digest + ".json")).read_bytes()
    snapshot = ExecutionSnapshot.model_validate_json(raw)
    if _hash(raw) != digest or snapshot.content_hash() != digest:
        raise WorkflowError("identity_mismatch")
    store.pack(snapshot)
    return snapshot


class _FrozenExecution(Execution):
    """A read-only historical view for core validation; never changes the journal."""

    def __init__(self, store: Execution, snapshot: ExecutionSnapshot) -> None:
        super().__init__(store.directory)
        self.snapshot = snapshot

    def read(self) -> ExecutionSnapshot:
        return self.snapshot

    def _write(self, snapshot: ExecutionSnapshot) -> None:
        raise WorkflowError("not_permitted")


def _binding(snapshot: ExecutionSnapshot, attempt: Attempt, step_id: str) -> FinancialBinding:
    return _parse(
        FinancialBinding,
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


def _historical(store: Execution, binding: FinancialBinding) -> _FrozenExecution:
    snapshot = _snapshot(store, binding.snapshot_sha256)
    attempt = next(a for a in snapshot.attempts if a.ticket_id == binding.ticket_id)
    sequence = ("source_readiness",) if attempt.module_id == "CP-0" else CP1_PROMOTION
    if (
        _binding(snapshot, attempt, binding.step_id) != binding
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


def _projection(store: Execution, binding: FinancialBinding) -> tuple[str, str]:
    historical = _historical(store, binding)
    attempt = next(a for a in historical.read().attempts if a.ticket_id == binding.ticket_id)
    if binding.step_id == "quality":
        inputs = cp1_quality_inputs(cp1_registers(historical, attempt.ticket_id))
        return inputs.content_hash(), inputs.model_dump_json()
    if binding.step_id not in ("narrative", "readiness"):
        raise WorkflowError("not_permitted")
    for index, step in enumerate(attempt.steps, 1):
        outcome = validate_cp1_stage(
            historical,
            historical.pack(),
            attempt.model_copy(update={"steps": attempt.steps[:index]}),
        )
        if outcome.issues or not outcome.retained_as(step):
            raise WorkflowError("identity_mismatch")
    step = attempt.steps[-1]
    if step.output_sha256 is None:
        raise WorkflowError("identity_mismatch")
    raw = historical.step_output(step.output_sha256)
    if binding.step_id == "narrative":
        stage = FinancialStage.model_validate_json(raw)
        return stage.narrative_inputs.content_hash(), narrative_evidence(stage)
    downstream = DownstreamInputs.model_validate_json(raw)
    return downstream.content_hash(), readiness_inputs(downstream)


def _filled(
    store: Execution, binding: FinancialBinding, payload: str
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if binding.step_id == "source_readiness":
        return payload, (), (), ()
    model = STEPS[binding.step_id].schema
    normal, resolved = normalise(model, payload)
    filled = prefill(
        model,
        normal,
        known_bindings(store, binding.ticket_id, binding.step_id),
        PREFILLED[binding.step_id],
    )
    return filled.payload, resolved, filled.paths, filled.kinds


def _evidence_issues(
    store: Execution, binding: FinancialBinding, payload: str, evidence: SourceEvidence
) -> tuple[str, ...]:
    if binding.step_id not in SOURCE_STEPS:
        return ()
    context = None
    if binding.step_id == "financials":
        attempt = next(a for a in store.read().attempts if a.ticket_id == binding.ticket_id)
        context = SourceContextReview.model_validate_json(
            store.payload(attempt.steps[0].payload_sha256)
        )
    issues = list(
        ToolRules().issues(binding.step_id, payload, seen=evidence.seen(), context=context)
    )
    if context is None:
        return tuple(issues)
    financial_ids = tuple(s.source_id for s in context.sources if s.classification == "financial")
    pack = store.pack()
    required = {
        (source.source_id, span.locator)
        for source in pack.sources
        if source.source_id in financial_ids and source.status == "ready"
        for span in source.spans
        if STATEMENT_HEADING.search(span.text)
    }
    if not required or not required <= set(evidence.extracted):
        issues.append("Financials must extract every located statement page in this epoch")
    tables = seen_tables(PackTools(pack, sources=financial_ids), evidence.seen(), context)
    try:
        submission = FinancialSubmission.model_validate_json(payload)
    except ValueError:
        return tuple(issues)  # The real core supplies shape errors.
    measured = set()
    for table in tables:
        key = (table.source_id, table.locator)
        if key not in required:
            continue
        if table.lines:
            measured.add(key)
        for extracted in table.lines:
            caption = (extracted.caption or "").upper()
            statement = (
                "IS"
                if "INCOME" in caption or "OPERATIONS" in caption
                else "CFS"
                if "CASH FLOW" in caption
                else "BS"
                if "BALANCE SHEET" in caption
                else None
            )
            covered = False
            for book in submission.financial.books:
                columns = _column_periods(table.headers, book.periods)
                if columns is None or len(columns) != len(extracted.values):
                    continue
                if all(
                    any(
                        line.period_id == period_id
                        and line.statement == statement
                        and " ".join(line.label.split()) == " ".join(extracted.label.split())
                        and line.value.amount == value
                        and any(
                            c.source_id == table.source_id
                            and c.locator == table.locator
                            and extracted.label in c.quote
                            for c in line.value.citations
                        )
                        for line in book.statement_lines
                    )
                    for period_id, value in zip(columns, extracted.values, strict=True)
                ):
                    covered = True
                    break
            if not covered:
                issues.append(
                    f"Uncovered extracted statement line: {table.source_id} {table.locator} line {extracted.line_no}"
                )
    if measured != required:
        issues.append("Statement extraction is unmeasured; empty tables do not establish coverage")
    return tuple(issues)


def _column_periods(headers: tuple[str, ...], periods: Any) -> tuple[str, ...] | None:
    """Map explicit quarter, FY and date headings; no inferred periods or arithmetic."""
    for header in headers:
        cells = re.split(r"\s{2,}", header.strip())[1:]
        if not cells:
            continue
        found = []
        for cell in cells:
            quarter = re.fullmatch(r"Q([1-4]) (\d{4})", cell)
            annual = re.fullmatch(r"FY (\d{4})", cell)
            dated = re.fullmatch(r"(Opening|Q[1-4]|FY) (\d{4}-\d{2}-\d{2})", cell)
            match_count = 0
            for period in periods:
                if (
                    quarter
                    and period.period_type == "QUARTER"
                    and period.fiscal_quarter == int(quarter[1])
                    and re.findall(r"\d{4}", period.fiscal_year) == [quarter[2]]
                ):
                    match_id = period.period_id
                elif (
                    annual
                    and period.period_type == "FY"
                    and re.findall(r"\d{4}", period.fiscal_year) == [annual[1]]
                ):
                    match_id = period.period_id
                elif (
                    dated
                    and str(period.end_date) == dated[2]
                    and (
                        (dated[1] == "Opening" and period.period_type == "PERIOD_END")
                        or (dated[1] == "FY" and period.period_type == "FY")
                        or (
                            dated[1].startswith("Q")
                            and period.period_type == "QUARTER"
                            and period.fiscal_quarter == int(dated[1][1])
                        )
                    )
                ):
                    match_id = period.period_id
                else:
                    continue
                match_count += 1
            if match_count != 1:
                break
            found.append(match_id)
        if len(found) == len(cells) and len(set(found)) == len(found):
            return tuple(found)
    return None


def _record(store: Execution, module_id: str) -> PromotedRecord:
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == module_id)
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    if (
        attempt.status != "finished"
        or attempt.issues
        or head.status not in ("accepted", "restricted")
    ):
        raise WorkflowError("identity_mismatch")
    return PromotedRecord(
        ticket_id=attempt.ticket_id, result_sha256=head.result_sha256, status=head.status
    )


def _files(directory: Path) -> dict[str, str]:
    return {name: _hash((directory / name).read_bytes()) for name in FILES}


class FinancialWorkflow:
    def __init__(self, store: Execution, attempt: Attempt, model_directory: Path) -> None:
        self._store, self._model_directory = store, model_directory
        self._operation = Lock()
        self._calls: list[FinancialCall] = []
        self._reads: list[InputRead] = []
        self._submissions: list[StageSubmission] = []
        self._publications: list[PublicationCall] = []
        self._refused_begin: RefusedBegin | None = None
        self._refusal: Literal["cp1_not_authorized"] | None = None
        self._model: ModelPublication | None = None
        self._participant = "trusted-python"
        self._transport: Literal["python-api", "bounded-json-lines/1"] = "python-api"
        self._limits: Counter[tuple[str, str, str]] = Counter()
        self._phase = "analytical"
        self._sealed = False
        self._activate(attempt, "source_readiness")

    @classmethod
    def create(
        cls, directory: Path, pack: PreparedPack, *, model_directory: Path
    ) -> "FinancialWorkflow":
        if pack.run.requested_modules != ("CP-1", "CP-MODEL"):
            raise WorkflowError("not_permitted")
        if (
            model_directory.exists()
            or model_directory.resolve() == directory.resolve()
            or directory.resolve() in model_directory.resolve().parents
        ):
            raise WorkflowError("not_permitted")
        store = Execution.create(directory, pack)
        return cls(store, store.begin("CP-0"), model_directory)

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
        self._binding = _binding(snapshot, attempt, step_id)
        self._current_sha256 = snapshot.content_hash()
        self._session = (
            SourceSession.from_execution(self._store, attempt.ticket_id, step_id)
            if step_id in SOURCE_STEPS
            else None
        )
        self._epoch_calls: list[FinancialCall] = []
        _historical(self._store, self._binding)

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            self._current()
            key = (self._binding.ticket_id, self._binding.step_id, "invoke")
            if self._phase != "analytical" or self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            if self._session is None:
                call = FinancialCall(
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
                call = _parse(FinancialCall, self._session.invoke(tool_name, arguments))
            call = _parse(FinancialCall, call.model_dump(mode="json"))
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
            if self._phase != "analytical" or self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            digest, body = _projection(self._store, self._binding)
            self._limits[key] += 1
            record = InputRead(
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
            if self._session is None and not any(r.binding == self._binding for r in self._reads):
                raise WorkflowError("not_permitted")
            evidence = (
                self._epoch_calls[-1].source_evidence if self._epoch_calls else SourceEvidence()
            )
            payload_bytes = payload.encode()
            binding = FinancialSubmissionBinding(
                binding=self._binding,
                payload_sha256=_hash(payload_bytes),
                call_ids=tuple(c.call_id for c in self._epoch_calls),
                successful_call_ids=tuple(c.call_id for c in self._epoch_calls if c.status == "ok"),
                source_evidence=evidence,
            )
            if (
                self._session is not None
                and _parse(FinancialSubmissionBinding, self._session.bind_submission(payload))
                != binding
            ):
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "payloads", binding.payload_sha256), payload_bytes)
            _retain(self._store, "bindings", binding)
            stored, resolved, paths, kinds = _filled(self._store, self._binding, payload)
            stored_bytes = stored.encode()
            stored_hash = _hash(stored_bytes)
            _put(_audit(self._store, "payloads", stored_hash), stored_bytes)
            issues = _evidence_issues(self._store, self._binding, stored, evidence)
            self._current()
            attempt = None
            disposition: Literal["valid", "invalid", "refused"] = "refused"
            submitted_step = None
            if not issues:
                if self._binding.step_id == "source_readiness":
                    attempt = submit_cp0_review(self._store, self._binding.ticket_id, stored)
                else:
                    submitted = submit_model_payload(
                        self._store, self._binding.ticket_id, self._binding.step_id, payload
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
                    if attempt.steps and attempt.steps[-1].step_id == self._binding.step_id
                    else attempt.step_repairs
                )
                if (
                    not candidates
                    or candidates[-1].payload_sha256 != stored_hash
                    or candidates[-1].step_id != self._binding.step_id
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
                canonical = (
                    SCHEMAS[self._binding.step_id].model_validate_json(stored).content_hash()
                )
            except ValueError:
                canonical = None
            after_hash = after.content_hash()
            record = StageSubmission(
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
            step_id = self._binding.step_id
            self._current_sha256 = after_hash
            if attempt is not None:
                if disposition == "valid" and step_id == "source_readiness":
                    try:
                        self._activate(self._store.begin("CP-1"), "source_context")
                    except NotAuthorized as error:
                        self._refusal = "cp1_not_authorized"
                        self._refused_begin = RefusedBegin(
                            snapshot_sha256=after_hash, reason=str(error)
                        )
                        _retain(self._store, "refused-begin", self._refused_begin)
                        self._phase = "not_authorized"
                elif disposition == "valid" and step_id == "quality":
                    self._phase = "promoted"
                elif disposition == "valid":
                    self._activate(attempt, CP1_PROMOTION[len(attempt.steps)])
                elif attempt.status == "pending":
                    self._activate(attempt, step_id)
                elif attempt.number == 0:
                    self._activate(
                        self._store.begin(attempt.module_id),
                        "source_readiness" if attempt.module_id == "CP-0" else "source_context",
                    )
                else:
                    self._phase = "failed"
            return {
                "schema_version": "financial-review-outcome/1",
                "status": disposition,
                "issues": list(issues),
                "step_id": step_id,
                "refusal": self._refusal,
                "snapshot_sha256": self._current_sha256,
                "next_step": self._binding.step_id if self._phase == "analytical" else None,
                "stored_payload_sha256": stored_hash,
                "prefilled": list(paths),
            }

    def publish_model(self) -> dict[str, Any]:
        with self._locked():
            before = self._current()
            if self._phase not in ("promoted", "not_authorized") or len(self._publications) >= 2:
                raise WorkflowError("not_permitted")
            ticket = None
            reason = None
            files: dict[str, str] = {}
            status: Literal["published", "refused", "failed"] = "refused"
            try:
                attempt = publish_cp_model(self._store, output=self._model_directory)
                ticket = attempt.ticket_id
                if verify_cp_model_publication(self._store, self._model_directory):
                    raise WorkflowError("identity_mismatch")
                model = _record(self._store, "CP-MODEL")
                cp1 = _record(self._store, "CP-1")
                files = _files(self._model_directory)
                self._model = ModelPublication(
                    ticket_id=model.ticket_id,
                    result_sha256=model.result_sha256,
                    cp1_result_sha256=cp1.result_sha256,
                    files=files,
                )
                status = "published"
                self._phase = "complete"
            except Exception as error:  # noqa: BLE001 - finalize every owned partial publication
                reason = str(error)
                after = self._store.read()
                new = [
                    a
                    for a in after.attempts
                    if a.ticket_id not in {a.ticket_id for a in before.attempts}
                ]
                if new:
                    status = "failed"
                    ticket = new[0].ticket_id if len(new) == 1 else None
                    if len(new) != 1 or new[0].module_id != "CP-MODEL":
                        self._phase = "failed"
                        raise WorkflowError("identity_mismatch") from error
                    if new[0].status == "pending":
                        try:
                            self._store.interrupt(
                                new[0].ticket_id, "Publication did not complete: " + reason
                            )
                        except Exception as cleanup_error:  # noqa: BLE001 - quarantine remains independent
                            reason += "; interruption failed: " + type(cleanup_error).__name__
                            self._phase = "failed"
                    if self._model_directory.exists():
                        for name in FILES:
                            try:
                                path = self._model_directory / name
                                if path.is_file():
                                    files[name] = _hash(path.read_bytes())
                            except OSError as hash_error:
                                reason += "; partial hash failed: " + type(hash_error).__name__
                        try:
                            self._model_directory.rename(
                                self._model_directory.with_name(
                                    self._model_directory.name + ".failed-" + str(uuid4())
                                )
                            )
                        except OSError as quarantine_error:
                            reason += "; quarantine failed: " + type(quarantine_error).__name__
                            self._phase = "failed"
                    if any(h.module_id == "CP-MODEL" for h in self._store.read().heads):
                        self._phase = "failed"
                elif self._phase == "not_authorized" and isinstance(error, CpModelRefused):
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
                else self._refusal or "publication_refused",
                "snapshot_sha256": self._current_sha256,
            }

    def write_receipt(self, destination: Path) -> FinancialSliceReceipt:
        with self._locked():
            snapshot = self._current()
            if self._phase != "complete":
                raise WorkflowError("not_permitted")
            receipt = FinancialSliceReceipt(
                run=snapshot.run,
                pack_sha256=snapshot.pack_sha256,
                snapshot_sha256=snapshot.content_hash(),
                participant=self._participant,
                transport=self._transport,
                cp0=_record(self._store, "CP-0"),
                cp1=None if self._refusal else _record(self._store, "CP-1"),
                model=self._model,
                refusal=self._refusal,
                calls=tuple(self._calls),
                input_reads=tuple(self._reads),
                submissions=tuple(self._submissions),
                refused_begin=self._refused_begin,
                publications=tuple(self._publications),
            )
            _verify(
                self._store,
                receipt,
                model_directory=None if self._refusal else self._model_directory,
                sealed=False,
            )
            self._current()
            _put(
                self._store.directory / "financial-slice-audit" / "receipt.sha256",
                receipt.content_hash().encode(),
            )
            _put(destination, receipt.model_dump_json().encode())
            self._current()
            self._sealed = True
            return receipt


def _verify(
    store: Execution, receipt: FinancialSliceReceipt, *, model_directory: Path | None, sealed: bool
) -> None:
    from deploy_vii.execution import head_of

    snapshot = store.read()
    if (snapshot.run, snapshot.pack_sha256, snapshot.content_hash()) != (
        receipt.run,
        receipt.pack_sha256,
        receipt.snapshot_sha256,
    ):
        raise WorkflowError("stale_binding")
    store.pack(snapshot)
    expected_heads = {"CP-0"} if receipt.refusal else {"CP-0", "CP-1", "CP-MODEL"}
    if {h.module_id for h in snapshot.heads} != expected_heads or len(snapshot.heads) != len(
        expected_heads
    ):
        raise WorkflowError("identity_mismatch")
    for head in snapshot.heads:
        qualification = (
            PROMOTED
            if head.module_id == "CP-1"
            else PUBLISHED
            if head.module_id == "CP-MODEL"
            else None
        )
        if head != head_of(store.head_module(head), qualification):
            raise WorkflowError("identity_mismatch")
    retained_steps = Counter(
        (a.ticket_id, step.content_hash())
        for a in snapshot.attempts
        if a.module_id in ("CP-0", "CP-1")
        for step in (*a.steps, *a.step_repairs)
    )
    recorded_steps = Counter(
        (s.binding.binding.ticket_id, s.step_sha256)
        for s in receipt.submissions
        if s.disposition != "refused"
    )
    if retained_steps != recorded_steps:
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
    coordinates = [b.snapshot_sha256 for b in bindings] + [
        s.snapshot_after_sha256 for s in receipt.submissions
    ]
    coordinates += [p.snapshot_before_sha256 for p in receipt.publications] + [
        p.snapshot_after_sha256 for p in receipt.publications
    ]
    if any(digest not in ancestors for digest in coordinates):
        raise WorkflowError("identity_mismatch")
    if (
        sealed
        and (store.directory / "financial-slice-audit" / "receipt.sha256").read_text()
        != receipt.content_hash()
    ):
        raise WorkflowError("identity_mismatch")
    collections = {
        "calls": receipt.calls,
        "input-reads": receipt.input_reads,
        "submissions": receipt.submissions,
        "bindings": tuple(s.binding for s in receipt.submissions),
        "publications": receipt.publications,
        "refused-begin": () if receipt.refused_begin is None else (receipt.refused_begin,),
    }
    for kind, values in collections.items():
        expected = {v.content_hash(): v.model_dump_json().encode() for v in values}
        directory = store.directory / "financial-slice-audit" / kind
        actual = {p.name for p in directory.iterdir()} if directory.exists() else set()
        if actual != set(expected) or any(
            _audit(store, kind, digest).read_bytes() != raw for digest, raw in expected.items()
        ):
            raise WorkflowError("identity_mismatch")
    if len({c.call_id for c in receipt.calls}) != len(receipt.calls):
        raise WorkflowError("identity_mismatch")
    for records in (receipt.calls, receipt.input_reads):
        counts = Counter((record.binding.ticket_id, record.binding.step_id) for record in records)
        if any(count > MAX_CALLS for count in counts.values()):
            raise WorkflowError("identity_mismatch")
    submission_counts = Counter(
        (s.binding.binding.ticket_id, s.binding.binding.step_id) for s in receipt.submissions
    )
    if any(count > MAX_CALLS for count in submission_counts.values()):
        raise WorkflowError("identity_mismatch")
    _publication_history(store, receipt)
    replayed: dict[str, SourceSession] = {}
    for call in receipt.calls:
        historical = _historical(store, call.binding)
        key = call.binding.content_hash()
        prior = [
            c for c in receipt.calls if c.binding == call.binding and c.sequence < call.sequence
        ]
        if call.sequence != len(prior) + 1 or call.sequence > MAX_CALLS:
            raise WorkflowError("identity_mismatch")
        if call.binding.step_id in SOURCE_STEPS:
            if key not in replayed:
                replayed[key] = SourceSession.from_execution(
                    historical, call.binding.ticket_id, call.binding.step_id
                )
            expected_call = _parse(FinancialCall, replayed[key].invoke(call.tool, call.arguments))
            if expected_call.model_copy(update={"call_id": call.call_id}) != call:
                raise WorkflowError("identity_mismatch")
        elif (
            call.status != "refused"
            or call.error_code != "not_permitted"
            or call.body is not None
            or call.source_evidence != SourceEvidence()
        ):
            raise WorkflowError("identity_mismatch")
    for read in receipt.input_reads:
        digest, body = _projection(store, read.binding)
        prior_reads = [
            r
            for r in receipt.input_reads
            if r.binding.ticket_id == read.binding.ticket_id
            and r.binding.step_id == read.binding.step_id
            and r.sequence < read.sequence
        ]
        if (
            (read.inputs_sha256, read.body) != (digest, body)
            or read.sequence != len(prior_reads) + 1
            or read.sequence > MAX_CALLS
        ):
            raise WorkflowError("identity_mismatch")
    valid = []
    for sequence, submission in enumerate(receipt.submissions, 1):
        if submission.sequence != sequence:
            raise WorkflowError("identity_mismatch")
        binding = submission.binding
        historical = _historical(store, binding.binding)
        raw = _raw(store, binding.payload_sha256)
        filled, resolved, paths, kinds = _filled(historical, binding.binding, raw)
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
        issues = _evidence_issues(historical, binding.binding, filled, evidence)
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
        canonical = None
        try:
            canonical = SCHEMAS[binding.binding.step_id].model_validate_json(filled).content_hash()
        except ValueError:
            pass
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
            if binding.binding.step_id not in SOURCE_STEPS and not any(
                r.binding == binding.binding for r in receipt.input_reads
            ):
                raise WorkflowError("identity_mismatch")
        elif step.status != "invalid" or step.issues != submission.issues:
            raise WorkflowError("identity_mismatch")
    if _record(store, "CP-0") != receipt.cp0:
        raise WorkflowError("identity_mismatch")
    cp0_attempt = next(a for a in snapshot.attempts if a.ticket_id == receipt.cp0.ticket_id)
    _verify_cp0(store, snapshot, cp0_attempt)
    expected_steps = [
        (cp0_attempt.ticket_id, s.step_id, s.content_hash()) for s in cp0_attempt.steps
    ]
    if receipt.refusal:
        if (
            receipt.refusal != "cp1_not_authorized"
            or receipt.cp1 is not None
            or receipt.model is not None
            or model_directory is not None
            or receipt.refused_begin is None
        ):
            raise WorkflowError("identity_mismatch")
        if any(a.module_id != "CP-0" for a in snapshot.attempts) or any(
            h.module_id != "CP-0" for h in snapshot.heads
        ):
            raise WorkflowError("identity_mismatch")
        try:
            current_inputs(snapshot, "CP-1")
        except NotAuthorized as error:
            if (
                str(error) != receipt.refused_begin.reason
                or receipt.refused_begin.snapshot_sha256 != snapshot.content_hash()
            ):
                raise WorkflowError("identity_mismatch") from None
        else:
            raise WorkflowError("identity_mismatch")
        if len(receipt.publications) != 1:
            raise WorkflowError("identity_mismatch")
        publication = receipt.publications[0]
        with tempfile.TemporaryDirectory() as refused_directory:
            try:
                publish_cp_model(
                    _FrozenExecution(store, snapshot), output=Path(refused_directory) / "absent"
                )
            except CpModelRefused as error:
                if publication != PublicationCall(
                    snapshot_before_sha256=snapshot.content_hash(),
                    snapshot_after_sha256=snapshot.content_hash(),
                    status="refused",
                    reason=str(error),
                    ticket_id=None,
                    files={},
                ):
                    raise WorkflowError("identity_mismatch") from None
            else:
                raise WorkflowError("identity_mismatch")
    else:
        if (
            receipt.cp1 is None
            or receipt.model is None
            or receipt.refused_begin is not None
            or model_directory is None
        ):
            raise WorkflowError("identity_mismatch")
        if (
            _record(store, "CP-1") != receipt.cp1
            or set(receipt.model.files) != set(FILES)
            or _files(model_directory) != receipt.model.files
        ):
            raise WorkflowError("identity_mismatch")
        attempt = next(a for a in snapshot.attempts if a.ticket_id == receipt.cp1.ticket_id)
        _verify_promotion(store, snapshot, attempt)
        expected_steps += [(attempt.ticket_id, s.step_id, s.content_hash()) for s in attempt.steps]
        model = _record(store, "CP-MODEL")
        if (model.ticket_id, model.result_sha256, receipt.cp1.result_sha256) != (
            receipt.model.ticket_id,
            receipt.model.result_sha256,
            receipt.model.cp1_result_sha256,
        ):
            raise WorkflowError("identity_mismatch")
        if verify_cp_model_publication(store, model_directory):
            raise WorkflowError("identity_mismatch")
        _verify_model_settlement(store, snapshot, model_directory)
        if (
            not receipt.publications
            or receipt.publications[-1].status != "published"
            or receipt.publications[-1].ticket_id != model.ticket_id
            or receipt.publications[-1].files != receipt.model.files
            or receipt.publications[-1].snapshot_after_sha256 != snapshot.content_hash()
        ):
            raise WorkflowError("identity_mismatch")
    if not all(item in valid for item in expected_steps):
        raise WorkflowError("identity_mismatch")
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise WorkflowError("stale_binding")


def _verify_cp0(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    from deploy_vii.execution import settle
    from deploy_vii.readiness import build_readiness, validate_review

    if len(attempt.steps) != 1 or attempt.steps[0].status != "valid":
        raise WorkflowError("identity_mismatch")
    step = attempt.steps[0]
    review = ReadinessReview.model_validate_json(store.payload(step.payload_sha256))
    if validate_review(store.pack(snapshot), review):
        raise WorkflowError("identity_mismatch")
    candidate = build_readiness(store.pack(snapshot), review, attempt=attempt.number)
    if (
        candidate.content_hash() != step.output_sha256
        or store.step_output(step.output_sha256 or "") != candidate.model_dump_json()
    ):
        raise WorkflowError("identity_mismatch")
    finished, result = settle(
        snapshot,
        attempt,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("CP0 candidate differs",),
        pack=store.pack(snapshot),
        load=store.head_module,
    )
    if finished != attempt or result != store.head_module(
        next(h for h in snapshot.heads if h.module_id == "CP-0")
    ):
        raise WorkflowError("identity_mismatch")


def _publication_history(store: Execution, receipt: FinancialSliceReceipt) -> None:
    """Every begun Model attempt and non-begin refusal has its retained actual transition."""
    snapshot = store.read()
    attempts = {a.ticket_id: a for a in snapshot.attempts if a.module_id == "CP-MODEL"}
    recorded = Counter(p.ticket_id for p in receipt.publications if p.ticket_id is not None)
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
            if not receipt.refusal and not (
                publication.reason.startswith("Output ")
                and "already exists; publish into a new directory" in publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            continue
        before_tickets = {a.ticket_id for a in before.attempts}
        added = [a for a in after.attempts if a.ticket_id not in before_tickets]
        if (
            len(added) != 1
            or added[0].module_id != "CP-MODEL"
            or added[0].ticket_id != publication.ticket_id
            or added[0] != attempts.get(publication.ticket_id)
        ):
            raise WorkflowError("identity_mismatch")
        if tuple(
            a for a in after.attempts if a.ticket_id != publication.ticket_id
        ) != before.attempts or set(publication.files) - set(FILES):
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


def _verify_promotion(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Re-enter the public promotion validator with a non-writing finish probe."""
    from deploy_vii.execution import settle

    if (
        len(attempt.steps) != 5
        or tuple(s.step_id for s in attempt.steps) != CP1_PROMOTION
        or any(s.status != "valid" for s in attempt.steps)
    ):
        raise WorkflowError("identity_mismatch")
    if next(h for h in snapshot.heads if h.module_id == "CP-1").qualification != PROMOTED:
        raise WorkflowError("identity_mismatch")
    registers = cp1_registers(store, attempt.ticket_id)
    handoff = CP1Handoff.model_validate_json(
        store.step_output(attempt.steps[4].output_sha256 or "")
    )
    review = QualityReview.model_validate_json(store.payload(attempt.steps[4].payload_sha256))
    if handoff.registers_sha256 != registers.content_hash() or handoff.quality != assess_quality(
        cp1_quality_inputs(registers), review
    ):
        raise WorkflowError("identity_mismatch")

    class Probe(_FrozenExecution):
        def finish(self, ticket_id: str, payload: str, validator: Any, **kwargs: Any) -> Attempt:
            if ticket_id != attempt.ticket_id or payload != store.payload(
                attempt.payload_sha256 or ""
            ):
                raise WorkflowError("identity_mismatch")
            finished, result = settle(
                snapshot,
                attempt,
                payload,
                validator,
                pack=store.pack(snapshot),
                load=store.head_module,
            )
            if finished != attempt or result != store.result(attempt.result_sha256 or ""):
                raise WorkflowError("identity_mismatch")
            return finished

    pending = attempt.model_copy(update={"status": "pending"})
    probe_snapshot = snapshot.model_copy(
        update={
            "attempts": tuple(
                pending if a.ticket_id == pending.ticket_id else a for a in snapshot.attempts
            )
        }
    )
    if (
        promote_cp1(
            Probe(store, probe_snapshot),
            attempt.ticket_id,
            store.payload(attempt.steps[4].payload_sha256),
        )
        != attempt
    ):
        raise WorkflowError("identity_mismatch")
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "envelope"
        write_cp1_envelope(store, destination)
        read_cp1_envelope(store, destination)


def _verify_model_settlement(
    store: Execution, snapshot: ExecutionSnapshot, directory: Path
) -> None:
    """The public publisher rebuilds the complete candidate; finish is a read-only probe."""
    from deploy_vii.execution import settle

    head = next(h for h in snapshot.heads if h.module_id == "CP-MODEL")
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)
    if head.qualification != PUBLISHED:
        raise WorkflowError("identity_mismatch")

    class Probe(_FrozenExecution):
        def begin(self, module_id: str) -> Attempt:
            if module_id != "CP-MODEL":
                raise WorkflowError("not_permitted")
            return attempt.model_copy(
                update={"status": "pending", "payload_sha256": None, "result_sha256": None}
            )

        def finish(self, ticket_id: str, payload: str, validator: Any, **kwargs: Any) -> Attempt:
            if ticket_id != attempt.ticket_id or payload != store.payload(
                attempt.payload_sha256 or ""
            ):
                raise WorkflowError("identity_mismatch")
            finished, result = settle(
                snapshot,
                attempt,
                payload,
                validator,
                pack=store.pack(snapshot),
                load=store.head_module,
            )
            if finished != attempt or result != store.result(head.result_sha256):
                raise WorkflowError("identity_mismatch")
            return finished

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "model"
        if publish_cp_model(Probe(store, snapshot), output=output) != attempt or _files(
            output
        ) != _files(directory):
            raise WorkflowError("identity_mismatch")


def verify_financial_slice_receipt(
    store: Execution, receipt: FinancialSliceReceipt, *, model_directory: Path | None = None
) -> None:
    """Authenticate portable sealed participation evidence and exact selected publication."""
    try:
        receipt = FinancialSliceReceipt.model_validate_json(receipt.model_dump_json())
        _verify(store, receipt, model_directory=model_directory, sealed=True)
    except WorkflowError:
        raise
    except (ValueError, OSError, KeyError, StopIteration, TypeError, UnicodeError):
        raise WorkflowError("identity_mismatch") from None


def serve_json_lines(
    workflow: FinancialWorkflow,
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
            elif operation == "publish_model" and set(request) == {"operation"}:
                result = workflow.publish_model()
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
        except Exception:  # noqa: BLE001 - sanitized bounded analytical transport
            result = {"status": "error", "error_code": "internal_error"}
        writer.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
        writer.flush()


def _nonfinite_json(value: str) -> None:
    raise ValueError("Non-finite JSON number")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded offline CP1 financial workflow")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--participant", required=True)
    args = parser.parse_args()
    pack = PreparedPack.model_validate_json(args.pack.read_bytes())
    workflow = FinancialWorkflow.create(args.directory, pack, model_directory=args.model_directory)
    serve_json_lines(
        workflow, sys.stdin, sys.stdout, destination=args.receipt, participant=args.participant
    )


if __name__ == "__main__":
    main()
