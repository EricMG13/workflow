"""Fresh CP0/CP1 foundation and immutable CP1B owner checkpoint.

Execution owns journal mutation and settlement; the earnings core owns arithmetic.
This adapter binds actual bounded participation to those existing authorities.
"""

from __future__ import annotations

import hashlib
import io
import itertools
import json
import math
import os
import re
from collections import Counter
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Annotated, Any, Literal, TextIO, cast
from uuid import uuid4

from pydantic import Field, JsonValue, StrictInt, ValidationError, field_validator, model_validator

from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    Hash,
    Identifier,
    Input,
    Module,
    ModuleView,
    ReportTable,
    Run,
    Source,
    Span,
    TableColumn,
    TableRow,
    Text,
)
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
    validate_cp1_stage,
)
from deploy_vii.downstream_readiness import DownstreamInputs, DownstreamReview
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    NotAuthorized,
    StepSubmission,
    StepValidation,
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
from deploy_vii.prose import tokenize
from deploy_vii.quality import QualityReview, assess_quality
from deploy_vii.readiness import ReadinessReview, citation_issues
from deploy_vii.source_context import SourceContextReview
from deploy_workflow.earnings import EarningsDeltaReport, build_earnings_delta
from deploy_workflow.financial_workflow import (
    STATEMENT_HEADING,
    FinancialBinding,
    FinancialCall,
    InputRead,
)
from deploy_workflow.host import SourceSession
from deploy_workflow.tools.upstream import UpstreamTools
from deploy_workflow.workflow import SourceEvidence

OwnerCaseId = Literal["E-QOQ-FLAT", "E-NO-YOY", "E-REQUIRED-CP1-MISSING"]
Transport = Literal["python-api", "bounded-json-lines/1"]
Phase = Literal[
    "source_readiness",
    "source_context",
    "financials",
    "narrative",
    "readiness",
    "quality",
    "earnings_delta",
    "complete",
    "failed",
]
OutcomeKind = Literal["owner_settled", "cp1_not_authorized"]
FactStatus = Literal["known", "missing", "conflicting", "not_applicable"]
JsonObject = dict[str, JsonValue]
_AttemptNo = Annotated[StrictInt, Field(ge=0, le=1)]
_Positive = Annotated[StrictInt, Field(ge=1)]
_Count = Annotated[StrictInt, Field(ge=0)]
_ERRORS = frozenset(
    {
        "bad_arguments",
        "not_permitted",
        "stale_binding",
        "identity_mismatch",
        "participation_incomplete",
        "transport_limit",
        "validation_failed",
        "internal_error",
    }
)


class OwnerError(ValueError):
    def __init__(self, code: str) -> None:
        if code not in _ERRORS:
            raise ValueError("bad_arguments")
        super().__init__(code)
        self.code = code


class WorkflowState(Contract):
    phase: Phase
    module_id: Literal["CP-0", "CP-1", "CP-1B"] | None
    step_id: str | None
    ticket_id: Identifier | None
    attempt: _AttemptNo | None
    prior_period_id: Identifier
    current_period_id: Identifier
    outcome: OutcomeKind | None

    @model_validator(mode="after")
    def active_identity(self) -> WorkflowState:
        active = (self.module_id, self.step_id, self.ticket_id, self.attempt)
        if self.phase in {"complete", "failed"}:
            if any(x is not None for x in active):
                raise ValueError("terminal state has no active identity")
        elif any(x is None for x in active) or self.outcome is not None:
            raise ValueError("active state requires its ticket identity")
        return self


class OwnerClose(Contract):
    schema_version: Literal["cp1b-owner-close/1"] = "cp1b-owner-close/1"
    outcome: OutcomeKind
    owner_receipt_sha256: Hash
    owner_snapshot_sha256: Hash


class ReviewOutcome(Contract):
    schema_version: Literal["cp1b-review-outcome/1"] = "cp1b-review-outcome/1"
    module_id: str
    step_id: str
    ticket_id: Identifier
    attempt: _AttemptNo
    disposition: Literal["valid", "invalid", "refused"]
    issue_count: _Count
    error_codes: tuple[str, ...]
    snapshot_sha256: Hash
    next_phase: Phase
    stored_payload_sha256: Hash | None

    @field_validator("error_codes")
    @classmethod
    def public_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not set(value) <= _ERRORS:
            raise ValueError("unrecognized owner error category")
        return value


class OwnerBinding(Contract):
    run_id: Identifier
    issuer_id: Identifier
    as_of: str
    method_version: str
    pack_sha256: Hash
    snapshot_sha256: Hash
    module_id: Literal["CP-1B"]
    step_id: Literal["earnings_delta"]
    ticket_id: Identifier
    attempt: _AttemptNo
    inputs: tuple[Input, ...]


class FactReference(Contract):
    producer_module_id: Literal["CP-1"]
    producer_sha256: Hash
    fact_id: Identifier
    table_id: Identifier
    row_id: Identifier
    field: Identifier


class CitationHandle(Contract):
    source_id: Identifier
    source_sha256: Hash
    locator: Text


class OperandReference(Contract):
    fact: FactReference
    period_id: Identifier
    basis_id: Identifier
    source_period: Text
    source_basis: Text
    fact_sha256: Hash
    citation_handles: tuple[CitationHandle, ...]


class OperandLineage(Contract):
    measure_id: Identifier
    prior: OperandReference | None
    current: OperandReference
    companions: tuple[FactReference, ...]


class MeasureSelection(Contract):
    measure_id: Identifier
    prior_fact_id: Identifier | None
    current_fact_id: Identifier
    companion_fact_ids: tuple[Identifier, ...]


class EarningsDeltaReview(Contract):
    schema_version: Literal["cp1b-review/1"] = "cp1b-review/1"
    prior_period_id: Identifier
    current_period_id: Identifier
    selections: Annotated[tuple[MeasureSelection, ...], Field(min_length=12, max_length=12)]
    comparison_assessment: Literal["flat_sequential", "comparative_not_supplied"]
    driver_assessment: Literal["not_supplied"]
    guidance_assessment: Literal["not_supplied"]


class EarningsPointRecord(Contract):
    measure_id: str
    prior_fact_id: str | None
    current_fact_id: str
    companion_fact_ids: tuple[str, ...]
    prior_value: Decimal | None
    current_value: Decimal | None
    prior_status: FactStatus
    current_status: FactStatus
    delta: Decimal | None
    delta_status: FactStatus
    delta_unit: str
    growth: Decimal | None
    growth_status: FactStatus
    reason: str | None
    unit: str
    currency: str | None
    scale: Decimal


class EarningsReportRecord(Contract):
    producer_sha256: str
    prior_period_id: str
    current_period_id: str
    prior_basis_id: str | None
    current_basis_id: str
    points: tuple[EarningsPointRecord, ...]
    limitations: tuple[str, ...]


class OwnerToolReceipt(Contract):
    schema_version: Literal["tool-receipt/1"] = "tool-receipt/1"
    call_id: str
    sequence: _Positive
    binding: OwnerBinding
    tool: str
    arguments: JsonObject
    status: Literal["ok", "refused", "error"]
    body: JsonObject | None
    error_code: str | None
    source_evidence: SourceEvidence

    @field_validator("source_evidence")
    @classmethod
    def no_raw_source_credit(cls, value: SourceEvidence) -> SourceEvidence:
        if value != SourceEvidence():
            raise ValueError("owner has no raw source authority")
        return value


class OwnerSession(Contract):
    session_id: Identifier
    index: _Positive
    binding: OwnerBinding
    normalized_grant_json: Text
    access_manifest_json: Text


class OwnerAccessRead(Contract):
    schema_version: Literal["cp1b-access-read/1"] = "cp1b-access-read/1"
    session_id: Identifier
    sequence: _Positive
    binding: OwnerBinding
    access_manifest_json: Text


class OwnerToolCall(Contract):
    schema_version: Literal["cp1b-owner-call/1"] = "cp1b-owner-call/1"
    ordinal: _Positive
    session_id: Identifier
    receipt: OwnerToolReceipt


class EarningsParticipation(Contract):
    schema_version: Literal["cp1b-participation/1"] = "cp1b-participation/1"
    binding: OwnerBinding
    session_id: Identifier
    grant_sha256: Hash
    manifest_sha256: Hash
    access_read_sha256: Hash
    call_ids: tuple[str, ...]
    successful_call_ids: tuple[str, ...]
    manifest_call_ids: tuple[str, ...]
    period_lookup_call_ids: tuple[str, ...]
    metric_lookup_call_ids: tuple[str, ...]
    citation_call_ids: tuple[str, ...]


class OwnerSubmissionEnvelope(Contract):
    schema_version: Literal["cp1b-owner-submission/1"] = "cp1b-owner-submission/1"
    binding: OwnerBinding
    raw_review_sha256: Hash
    review: EarningsDeltaReview
    participation: EarningsParticipation


class EarningsOwnerStage(Contract):
    schema_version: Literal["cp1b-owner-stage/1"] = "cp1b-owner-stage/1"
    review_sha256: Hash
    participation_sha256: Hash
    report: EarningsReportRecord
    operands: tuple[OperandLineage, ...]
    candidate: Module


class BoundSubmission(Contract):
    schema_version: Literal["cp1b-bound-submission/1"] = "cp1b-bound-submission/1"
    binding: FinancialBinding | OwnerBinding
    raw_payload_sha256: Hash
    stored_payload_sha256: Hash
    canonical_review_sha256: Hash | None
    call_ids: tuple[str, ...]
    successful_call_ids: tuple[str, ...]
    source_evidence: SourceEvidence
    input_read_hashes: tuple[Hash, ...]
    participation_sha256: Hash | None
    owner_session_id: Identifier | None
    normalization_paths: tuple[str, ...]
    prefilled_paths: tuple[str, ...]
    prefilled_kinds: tuple[str, ...]

    @model_validator(mode="after")
    def selected_session(self) -> BoundSubmission:
        if isinstance(self.binding, OwnerBinding) != (self.owner_session_id is not None):
            raise ValueError("owner session association differs from binding kind")
        return self


class SubmissionIntent(Contract):
    index: _Positive
    binding: BoundSubmission
    snapshot_before_sha256: Hash


class SubmissionOutcome(Contract):
    intent_sha256: Hash
    disposition: Literal["valid", "invalid", "refused"]
    issues: tuple[str, ...]
    snapshot_after_sha256: Hash
    step_sha256: Hash | None
    step_output_sha256: Hash | None
    candidate_sha256: Hash | None
    result_sha256: Hash | None


class BeginRecord(Contract):
    index: _Positive
    module_id: Literal["CP-0", "CP-1", "CP-1B"]
    snapshot_before_sha256: Hash
    snapshot_after_sha256: Hash
    ticket_id: Identifier | None
    attempt: _AttemptNo | None
    error_code: Literal["not_authorized", "not_permitted"] | None


class OwnerHeadRecord(Contract):
    ticket_id: Identifier
    attempt: _AttemptNo
    head: Head
    candidate_sha256: Hash
    step_sha256s: tuple[Hash, ...]


class SourceIdentity(Contract):
    source_id: Identifier
    status: Literal["ready", "missing", "unreadable"]
    sha256: Hash | None


class OwnerPins(Contract):
    case_manifest_sha256: Hash
    source_manifest_sha256: Hash
    core_expected_sha256: Hash
    access_expected_sha256: Hash
    render_expected_sha256: Hash
    owner_expected_sha256: Hash
    sources: tuple[SourceIdentity, ...]


class OwnerSetup(Contract):
    schema_version: Literal["cp1b-owner-setup/1"] = "cp1b-owner-setup/1"
    run: Run
    pack_sha256: Hash
    initial_snapshot_sha256: Hash
    case_id: OwnerCaseId
    pins: OwnerPins
    participant: Text
    transport: Transport
    policy_sha256: Hash


class TransportMessage(Contract):
    index: _Positive
    operation: Literal["state", "invoke", "read_inputs", "submit_review", "close", "invalid"]
    request_sha256: Hash


class AuditEntry(Contract):
    kind: Literal[
        "transport-messages",
        "begins",
        "foundation-calls",
        "foundation-reads",
        "owner-sessions",
        "owner-reads",
        "owner-calls",
        "bindings",
        "intents",
        "outcomes",
        "participations",
        "stages",
        "payloads",
        "setup",
    ]
    sha256: Hash


class EarningsOwnerReceipt(Contract):
    schema_version: Literal["cp1b-owner-receipt/1"] = "cp1b-owner-receipt/1"
    run: Run
    pack_sha256: Hash
    owner_snapshot_sha256: Hash
    case_id: OwnerCaseId
    pins: OwnerPins
    participant: Text
    transport: Transport
    outcome: OutcomeKind
    cp0: OwnerHeadRecord
    cp1: OwnerHeadRecord | None
    cp1b: OwnerHeadRecord | None
    cp1b_stage_sha256: Hash | None
    transport_messages: tuple[TransportMessage, ...]
    begins: tuple[BeginRecord, ...]
    foundation_calls: tuple[FinancialCall, ...]
    foundation_input_reads: tuple[InputRead, ...]
    owner_sessions: tuple[OwnerSession, ...]
    owner_access_reads: tuple[OwnerAccessRead, ...]
    owner_calls: tuple[OwnerToolCall, ...]
    submission_intents: tuple[SubmissionIntent, ...]
    submission_outcomes: tuple[SubmissionOutcome, ...]
    audit_inventory: tuple[AuditEntry, ...]
    publication_files: tuple[str, ...]

    @model_validator(mode="after")
    def owner_boundary(self) -> EarningsOwnerReceipt:
        if self.publication_files:
            raise ValueError("owner checkpoint has no publication")
        if self.outcome == "owner_settled":
            if self.cp1 is None or self.cp1b is None or self.cp1b_stage_sha256 is None:
                raise ValueError("settled owner requires complete foundation and stage")
        elif any(x is not None for x in (self.cp1, self.cp1b, self.cp1b_stage_sha256)) or any(
            (
                self.owner_sessions,
                self.owner_access_reads,
                self.owner_calls,
            )
        ):
            raise ValueError("missing CP1 cannot have owner results or participation")
        return self


MAX_LINE = 4194304
MAX_JSON_DEPTH = 100  # nesting bound, well below pydantic's JSON limit of 200
MAX_MESSAGES = 2048
MAX_OWNER_CALLS = 1024
MAX_OWNER_SESSIONS = 16
MAX_ACCESS_READS = 16
MAX_FOUNDATION = 16
MAX_AUDIT = 16384
MAX_RECEIPT = 67108864
_SOURCE_PHASES = frozenset({"source_readiness", "source_context", "financials"})
_MEASURES = (
    "revenue",
    "ebitda",
    "adjusted_ebitda",
    "ebitda_margin",
    "cfo_reported",
    "capex",
    "fcf",
    "cash_closing",
    "total_debt",
    "net_debt",
    "total_leverage_reported",
    "net_leverage_reported",
)
_PROJECTED = tuple(
    sorted(
        (
            "amount",
            "basis",
            "calculation_id",
            "calculation_status",
            "citation_handles",
            "currency",
            "denominator",
            "fact_id",
            "field",
            "label",
            "limitation",
            "period",
            "row_id",
            "scale",
            "status",
            "table_id",
            "text",
            "unit",
            "value_class",
        )
    )
)
_SCHEMAS: dict[str, type[Contract]] = {
    "source_readiness": ReadinessReview,
    "source_context": SourceContextReview,
    "financials": FinancialSubmission,
    "narrative": NarrativeReview,
    "readiness": DownstreamReview,
    "quality": QualityReview,
    "earnings_delta": EarningsDeltaReview,
}
_KINDS: dict[str, type[Contract]] = {
    "setup": OwnerSetup,
    "transport-messages": TransportMessage,
    "begins": BeginRecord,
    "foundation-calls": FinancialCall,
    "foundation-reads": InputRead,
    "owner-sessions": OwnerSession,
    "owner-reads": OwnerAccessRead,
    "owner-calls": OwnerToolCall,
    "bindings": BoundSubmission,
    "intents": SubmissionIntent,
    "outcomes": SubmissionOutcome,
    "participations": EarningsParticipation,
    "stages": EarningsOwnerStage,
}
_PINS = {
    "manifest.json": "60ed95782648064db7806bb7f0714fe030f9563424df50e17500803a2edfb7ec",
    "source_manifest": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
    "expected.json": "041e2e05cec282658e28a9f99f1c2e93e6f6d8c2ab17d790aad760676a6c2599",
    "access-expected.json": "a8210ba05e81c3cba04634bfe82e3e7aa11525892407b41d379ebf0298413d0c",
    "render-expected.json": "7b45f939d2d771611e9b11633f348e7c1174cb7ea0b3eb36eeb20661dc4192c4",
    "owner-expected.json": "a37dc25f8f756364ae88726cdec3f2de1bbf4c20892ca910d22e9646186efd9d",
}
_POLICY_SHA256 = "7fba44bc1cf2d2dd8b26ed941c28b04371ce29f1875f070f48dc6d12b7efa8d6"
_SESSION_POLICY_SHA256 = "7c2e03125b0b48a914b311d84178894b7487250fe0d4934c7549fca8c777afd4"
_CASE_MANIFEST = Path(__file__).resolve().parents[2] / "cases/earnings/manifest.json"


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def _text_depth(text: str) -> int:
    """Maximum bracket nesting of JSON-looking text, without recursion.

    Counts `[` and `{` outside string literals; it is a bound, not a parser, so
    malformed text is measured the same way and rejected later by the real parser.
    """
    depth = deepest = 0
    in_string = escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            deepest = max(deepest, depth)
        elif char in "]}" and depth:
            depth -= 1
    return deepest


def _json_copy(value: object) -> JsonValue:
    """Validate exact JSON types before serialization; invoke no user copy hooks."""
    active: set[int] = set()

    def visit(item: object, depth: int) -> None:
        if item is None or type(item) in {str, bool, int}:
            return
        if type(item) is float and math.isfinite(item):
            return
        # The receipt models re-parse these values with pydantic, which rejects
        # nesting from depth 200; refuse here, before any tool consumes a sequence.
        if type(item) not in {dict, list} or id(item) in active or depth >= MAX_JSON_DEPTH:
            raise OwnerError("bad_arguments")
        active.add(id(item))
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise OwnerError("bad_arguments")
                visit(child, depth + 1)
        else:
            for child in cast(list[object], item):
                visit(child, depth + 1)
        active.remove(id(item))

    try:
        visit(value, 0)
        return cast(JsonValue, json.loads(_canonical(value).encode("utf-8")))
    except (RecursionError, ValueError):
        # ValueError covers UnicodeEncodeError and the interpreter's integer-digit
        # limit (json.dumps of an int over 4300 digits); both are actor input.
        raise OwnerError("bad_arguments") from None


def _parse[T: Contract](model: type[T], value: Any) -> T:
    return model.model_validate_json(_canonical(value))


_PENDING = ".pending-"


def _is_put_residue(path: Path) -> bool:
    """A temp file `_put` left behind by a crash; it is never a record or evidence."""
    return re.fullmatch(r"\.pending-[0-9a-f]{32}", path.name) is not None and path.is_file()


def _put(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / (_PENDING + uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise OwnerError("identity_mismatch") from None
    finally:
        temporary.unlink(missing_ok=True)


def _sealed_on_disk(store: Execution) -> bool:
    return (store.directory / "earnings-owner-audit/owner-receipt.sha256").exists()


def _audit(store: Execution, kind: str, digest: str) -> Path:
    return store.directory / "earnings-owner-audit" / kind / digest


def _retain(store: Execution, kind: str, record: Contract) -> None:
    path = _audit(store, kind, record.content_hash())
    if not path.exists() and len(_inventory(store)) >= MAX_AUDIT:
        raise OwnerError("transport_limit")
    _put(path, record.model_dump_json().encode())


def _payload(store: Execution, raw: bytes) -> str:
    digest = _hash(raw)
    path = _audit(store, "payloads", digest)
    if not path.exists() and len(_inventory(store)) >= MAX_AUDIT:
        raise OwnerError("transport_limit")
    _put(path, raw)
    return digest


@contextmanager
def _stored_read() -> Iterator[None]:
    """Refuse unreadable or malformed stored bytes as `identity_mismatch`.

    Fail-closed and limited to the stored-record read sites that wrap it: a missing
    file, a directory in place of a file, or bytes that do not decode or validate
    mean the stored evidence was altered. Errors raised by B1's own composition are
    never inside this context, so programming defects propagate (lease: unexpected
    programming/I/O failures propagate). The original error stays as `__cause__`.
    """
    try:
        yield
    except OwnerError:
        raise
    except (FileNotFoundError, IsADirectoryError, ValueError) as error:
        raise OwnerError("identity_mismatch") from error


def _head(store: Execution) -> ExecutionSnapshot:
    with _stored_read():
        return store.read()


def _stored_bytes(store: Execution, kind: str, digest: str) -> bytes:
    """The bytes of one stored audit record; an unreadable record is tampered or lost."""
    with _stored_read():
        return _audit(store, kind, digest).read_bytes()


def _raw(store: Execution, digest: str) -> bytes:
    raw = _stored_bytes(store, "payloads", digest)
    if _hash(raw) != digest:
        raise OwnerError("identity_mismatch")
    return raw


def _text(store: Execution, digest: str) -> str:
    """A stored payload as text; stored bytes that do not decode are tampered evidence."""
    raw = _raw(store, digest)
    with _stored_read():
        return raw.decode("utf-8")


def _known[K, V](order: Mapping[K, V], key: K) -> V:
    """Look `key` up in an index built from stored records; an unknown key is tamper.

    Every key comes from a stored record that must name another stored record or a
    snapshot on the authenticated chain, so a miss means a record was forged,
    altered or deleted (lease: conflicting or ambiguous evidence refuses).
    """
    if key not in order:
        raise OwnerError("identity_mismatch")
    return order[key]


def _records[T: Contract](store: Execution, kind: str, model: type[T]) -> tuple[T, ...]:
    folder = store.directory / "earnings-owner-audit" / kind
    if folder.exists() and not folder.is_dir():
        raise OwnerError("identity_mismatch")
    result = []
    for path in sorted(folder.iterdir()) if folder.exists() else ():
        if _is_put_residue(path):
            continue
        with _stored_read():
            raw = path.read_bytes()
            record = model.model_validate_json(raw)
        if path.name != _hash(raw) or record.model_dump_json().encode() != raw:
            raise OwnerError("identity_mismatch")
        result.append(record)
    return tuple(result)


def _inventory(store: Execution) -> tuple[AuditEntry, ...]:
    root = store.directory / "earnings-owner-audit"
    entries = []
    if root.exists():
        for path in root.iterdir():
            if _is_put_residue(path):
                continue
            if path.name in {"owner-receipt.json", "owner-receipt.sha256"}:
                if not path.is_file():
                    raise OwnerError("identity_mismatch")
                continue
            if path.name not in {*_KINDS, "payloads"} or not path.is_dir():
                raise OwnerError("identity_mismatch")
            for record in path.iterdir():
                if _is_put_residue(record):
                    continue
                if not record.is_file() or re.fullmatch("[0-9a-f]{64}", record.name) is None:
                    raise OwnerError("identity_mismatch")
                if _hash(record.read_bytes()) != record.name:
                    raise OwnerError("identity_mismatch")
                entries.append(_parse(AuditEntry, {"kind": path.name, "sha256": record.name}))
    if len(entries) > MAX_AUDIT:
        raise OwnerError("transport_limit")
    return tuple(sorted(entries, key=lambda e: (e.kind, e.sha256)))


def _snapshot(store: Execution, digest: str) -> ExecutionSnapshot:
    with _stored_read():
        raw = (store.directory / "snapshots" / (digest + ".json")).read_bytes()
        value = ExecutionSnapshot.model_validate_json(raw)
    if _hash(raw) != digest or value.content_hash() != digest:
        raise OwnerError("identity_mismatch")
    with _stored_read():
        store.pack(value)
    return value


class _FrozenExecution(Execution):
    def __init__(self, store: Execution, snapshot: ExecutionSnapshot) -> None:
        super().__init__(store.directory)
        self.snapshot = snapshot

    def read(self) -> ExecutionSnapshot:
        return self.snapshot

    def _load(self, sha256: str) -> bytes:
        # The core raises only for an invalid hash, a missing blob or a hash mismatch
        # (execution.py:554-562): each means a referenced journal blob is lost or altered.
        with _stored_read():
            return super()._load(sha256)

    def _write(self, snapshot: ExecutionSnapshot) -> None:
        raise OwnerError("not_permitted")


def _case_pins(
    case_manifest: Path, case_id: OwnerCaseId, pack: PreparedPack
) -> tuple[dict[str, Any], OwnerPins]:
    raw = case_manifest.read_bytes()
    if _hash(raw) != _PINS["manifest.json"]:
        raise OwnerError("identity_mismatch")
    descriptor = json.loads(raw)
    matches = [case for case in descriptor["cases"] if case["case_id"] == case_id]
    if len(matches) != 1:
        raise OwnerError("bad_arguments")
    case = matches[0]
    source_raw = (case_manifest.parent / descriptor["source_manifest"]).read_bytes()
    if _hash(source_raw) != _PINS["source_manifest"]:
        raise OwnerError("identity_mismatch")
    for name in (
        "expected.json",
        "access-expected.json",
        "render-expected.json",
        "owner-expected.json",
    ):
        if _hash((case_manifest.parent / name).read_bytes()) != _PINS[name]:
            raise OwnerError("identity_mismatch")
    if (
        _hash((case_manifest.parent / "session-binding-expected.json").read_bytes())
        != _SESSION_POLICY_SHA256
    ):
        raise OwnerError("identity_mismatch")
    source_manifest = json.loads(source_raw)
    sources = []
    for item in source_manifest["sources"]:
        missing = case["source_state"] == "financial_missing" and item["source_id"] == "financial"
        spans = () if missing else tuple(Span(**page) for page in item["pages"])
        if not missing and _hash("\f".join(span.text for span in spans).encode()) != item["sha256"]:
            raise OwnerError("identity_mismatch")
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["name"],
                status="missing" if missing else "ready",
                sha256=None if missing else item["sha256"],
                spans=spans,
                coverage=(),
                media_type=None,
                extractor="supplied-representation",
                extraction_status="blocked" if missing else "complete",
                limitation="Quarterly financial statements were not supplied."
                if missing
                else "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
                if item["source_id"] == "financial"
                else None,
            )
        )
    expected = PreparedPack(
        run=Run.model_validate_json(_canonical(case["run"])), sources=tuple(sources)
    )
    if pack != expected or pack.model_dump_json() != expected.model_dump_json():
        raise OwnerError("identity_mismatch")
    pins = OwnerPins(
        case_manifest_sha256=_PINS["manifest.json"],
        source_manifest_sha256=_PINS["source_manifest"],
        core_expected_sha256=_PINS["expected.json"],
        access_expected_sha256=_PINS["access-expected.json"],
        render_expected_sha256=_PINS["render-expected.json"],
        owner_expected_sha256=_PINS["owner-expected.json"],
        sources=tuple(
            SourceIdentity(source_id=s.source_id, status=s.status, sha256=s.sha256)
            for s in pack.sources
        ),
    )
    return case, pins


def _binding(
    snapshot: ExecutionSnapshot, attempt: Attempt, step: str
) -> FinancialBinding | OwnerBinding:
    data = {
        "run_id": snapshot.run.run_id,
        "issuer_id": snapshot.run.issuer_id,
        "as_of": snapshot.run.as_of.isoformat(),
        "method_version": snapshot.run.method_version,
        "pack_sha256": snapshot.pack_sha256,
        "snapshot_sha256": snapshot.content_hash(),
        "module_id": attempt.module_id,
        "step_id": step,
        "ticket_id": attempt.ticket_id,
        "attempt": attempt.number,
        "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
    }
    return (
        _parse(OwnerBinding, data)
        if attempt.module_id == "CP-1B"
        else _parse(FinancialBinding, data)
    )


def _historical(store: Execution, binding: FinancialBinding | OwnerBinding) -> _FrozenExecution:
    snapshot = _snapshot(store, binding.snapshot_sha256)
    matches = [a for a in snapshot.attempts if a.ticket_id == binding.ticket_id]
    if len(matches) != 1:
        raise OwnerError("identity_mismatch")
    attempt = matches[0]
    chain = (
        ("source_readiness",)
        if attempt.module_id == "CP-0"
        else (("earnings_delta",) if attempt.module_id == "CP-1B" else CP1_PROMOTION)
    )
    if (
        _binding(snapshot, attempt, binding.step_id) != binding
        or attempt.status != "pending"
        or attempt.issues
        or attempt.interruption is not None
        or attempt.payload_sha256 is not None
        or attempt.result_sha256 is not None
        or current_inputs(snapshot, attempt.module_id) != attempt.inputs
        or tuple(s.step_id for s in attempt.steps) != chain[: len(attempt.steps)]
        or any(s.status != "valid" for s in attempt.steps)
        or len(attempt.steps) >= len(chain)
        or chain[len(attempt.steps)] != binding.step_id
    ):
        raise OwnerError("identity_mismatch")
    return _FrozenExecution(store, snapshot)


def _projection(store: Execution, binding: FinancialBinding) -> tuple[str, str]:
    historical = _historical(store, binding)
    attempt = next(a for a in historical.read().attempts if a.ticket_id == binding.ticket_id)
    if binding.step_id == "quality":
        inputs = cp1_quality_inputs(cp1_registers(historical, attempt.ticket_id))
        return inputs.content_hash(), inputs.model_dump_json()
    if binding.step_id not in {"narrative", "readiness"}:
        raise OwnerError("not_permitted")
    for index, step in enumerate(attempt.steps, 1):
        validation = validate_cp1_stage(
            historical,
            historical.pack(),
            attempt.model_copy(update={"steps": attempt.steps[:index]}),
        )
        if validation.issues or not validation.retained_as(step):
            raise OwnerError("identity_mismatch")
    output = historical.step_output(attempt.steps[-1].output_sha256 or "")
    if binding.step_id == "narrative":
        stage = FinancialStage.model_validate_json(output)
        return stage.narrative_inputs.content_hash(), narrative_evidence(stage)
    downstream = DownstreamInputs.model_validate_json(output)
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


def _column_periods(headers: tuple[str, ...], periods: Any) -> tuple[str, ...] | None:
    """Only explicit source headings select reported columns; never infer aliases."""
    for header in headers:
        cells = re.split(r"\s{2,}", header.strip())[1:]
        if not cells:
            continue
        found = []
        for cell in cells:
            quarter = re.fullmatch(r"Q([1-4]) (\d{4})", cell)
            annual = re.fullmatch(r"FY (\d{4})", cell)
            dated = re.fullmatch(r"(Opening|Q[1-4]|FY) (\d{4}-\d{2}-\d{2})", cell)
            matches = []
            for period in periods:
                if (
                    (
                        quarter
                        and period.period_type == "QUARTER"
                        and period.fiscal_quarter == int(quarter[1])
                        and re.findall(r"\d{4}", period.fiscal_year) == [quarter[2]]
                    )
                    or (
                        annual
                        and period.period_type == "FY"
                        and re.findall(r"\d{4}", period.fiscal_year) == [annual[1]]
                    )
                    or (
                        dated
                        and str(period.end_date) == dated[2]
                        and (
                            dated[1] == "Opening"
                            and period.period_type == "PERIOD_END"
                            or dated[1] == "FY"
                            and period.period_type == "FY"
                            or dated[1].startswith("Q")
                            and period.period_type == "QUARTER"
                            and period.fiscal_quarter == int(dated[1][1])
                        )
                    )
                ):
                    matches.append(period.period_id)
            if len(matches) != 1:
                break
            found.append(matches[0])
        if len(found) == len(cells) and len(set(found)) == len(found):
            return tuple(found)
    return None


def _source_issues(
    store: Execution,
    binding: FinancialBinding,
    payload: str,
    evidence: SourceEvidence,
    calls: tuple[FinancialCall, ...],
) -> tuple[str, ...]:
    if binding.step_id not in _SOURCE_PHASES:
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
    pack = store.pack()
    if context is None:
        required_reads = {("identity", "page:1")}
        financial = next(s for s in pack.sources if s.source_id == "financial")
        if financial.status == "ready":
            required_reads.add(("financial", "page:1"))
        elif not any(
            call.tool == "read_pages"
            and call.status == "refused"
            and call.error_code == "unavailable"
            and call.body is None
            and call.arguments.get("source_id") == "financial"
            and type(call.arguments.get("first_page")) is int
            and type(call.arguments.get("last_page")) is int
            and call.arguments["first_page"] <= 1 <= call.arguments["last_page"]
            for call in calls
        ):
            issues.append("Missing financial source requires its actual unavailable-read refusal")
        if not required_reads <= set(evidence.read):
            issues.append(
                "Current source epoch must read the required identity and financial pages"
            )
        return tuple(issues)
    financial_ids = tuple(s.source_id for s in context.sources if s.classification == "financial")
    required_reads = {
        (s.source_id, span.locator)
        for s in pack.sources
        if s.source_id in financial_ids and s.status == "ready"
        for span in s.spans
    }
    if not required_reads <= set(evidence.read):
        issues.append("Financials must read every supplied financial page in this epoch")
    required = {
        (s.source_id, span.locator)
        for s in pack.sources
        if s.source_id in financial_ids and s.status == "ready"
        for span in s.spans
        if STATEMENT_HEADING.search(span.text)
    }
    if not required or not required <= set(evidence.extracted):
        issues.append("Financials must extract every located statement page in this epoch")
    tables = seen_tables(PackTools(pack, sources=financial_ids), evidence.seen(), context)
    try:
        submission = FinancialSubmission.model_validate_json(payload)
    except ValidationError:
        return tuple(issues)
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
                        line.period_id == pid
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
                    for pid, value in zip(columns, extracted.values, strict=True)
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


def _cp1_candidate(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> Module:
    if tuple(s.step_id for s in attempt.steps) != CP1_PROMOTION or any(
        s.status != "valid" for s in attempt.steps
    ):
        raise OwnerError("identity_mismatch")
    frozen = _FrozenExecution(store, snapshot)
    registers = cp1_registers(frozen, attempt.ticket_id)
    handoff = CP1Handoff.model_validate_json(
        frozen.step_output(attempt.steps[4].output_sha256 or "")
    )
    review = QualityReview.model_validate_json(frozen.payload(attempt.steps[4].payload_sha256))
    if handoff.registers_sha256 != registers.content_hash() or handoff.quality != assess_quality(
        cp1_quality_inputs(registers), review
    ):
        raise OwnerError("identity_mismatch")
    candidates: list[Module] = []

    class Probe(_FrozenExecution):
        def finish(self, ticket_id: str, payload: str, validator: Any, **kwargs: Any) -> Attempt:
            if ticket_id != attempt.ticket_id or kwargs.get("qualification") != PROMOTED:
                raise OwnerError("identity_mismatch")
            candidate = Module.model_validate_json(payload)
            if validator(candidate):
                raise OwnerError("identity_mismatch")
            candidates.append(candidate)
            return attempt

    pending = attempt.model_copy(update={"status": "pending"})
    historical = snapshot.model_copy(
        update={
            "attempts": tuple(
                pending if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            )
        }
    )
    promote_cp1(
        Probe(store, historical), attempt.ticket_id, frozen.payload(attempt.steps[4].payload_sha256)
    )
    if len(candidates) != 1:
        raise OwnerError("identity_mismatch")
    return candidates[0]


def _head_record(store: Execution, snapshot: ExecutionSnapshot, module_id: str) -> OwnerHeadRecord:
    heads = [h for h in snapshot.heads if h.module_id == module_id]
    if len(heads) != 1:
        raise OwnerError("identity_mismatch")
    head = heads[0]
    attempts = [
        a
        for a in snapshot.attempts
        if a.module_id == module_id and a.result_sha256 == head.result_sha256
    ]
    if len(attempts) != 1 or attempts[0].status != "finished" or attempts[0].payload_sha256 is None:
        raise OwnerError("identity_mismatch")
    attempt = attempts[0]
    candidate_sha256 = attempt.payload_sha256
    if candidate_sha256 is None:
        raise OwnerError("identity_mismatch")
    _FrozenExecution(store, snapshot).head_module(head)
    return OwnerHeadRecord(
        ticket_id=attempt.ticket_id,
        attempt=attempt.number,
        head=head,
        candidate_sha256=candidate_sha256,
        step_sha256s=tuple(s.content_hash() for s in attempt.steps),
    )


def _full_cp1(store: Execution, binding: OwnerBinding) -> tuple[Module, ModuleView]:
    historical = _historical(store, binding)
    snapshot = historical.read()
    record = _head_record(store, snapshot, "CP-1")
    producer = historical.head_module(record.head)
    run = snapshot.run
    if (
        record.head.qualification != PROMOTED
        or producer.status not in {"accepted", "restricted"}
        or (producer.run_id, producer.issuer_id, producer.as_of, producer.method_version)
        != (run.run_id, run.issuer_id, run.as_of, run.method_version)
        or producer.content_hash() != record.head.result_sha256
        or not any(
            i.input_id == "CP-1"
            and i.sha256 == producer.content_hash()
            and i.status == producer.status
            for i in binding.inputs
        )
    ):
        raise OwnerError("identity_mismatch")
    view = ModuleView(
        module_id="CP-1",
        title="Financials",
        aliases=(),
        status=producer.status,
        artifact_sha256=producer.content_hash(),
        facts=producer.facts,
        tables=producer.tables,
        claims=producer.claims,
        limitations=(*producer.limitations, *producer.inherited_limitations),
    )
    return producer, view


def _grant(
    store: Execution, binding: OwnerBinding, prior: str, current: str
) -> tuple[dict[str, Any], EarningsDeltaReport, Module]:
    producer, view = _full_cp1(store, binding)
    report = build_earnings_delta(view, prior, current)
    chosen = {f.fact_id: f for f in producer.facts if f.table_id == "T4.14"}
    metrics: dict[str, dict[str, Fact]] = {}
    for fact in producer.facts:
        if fact.table_id == "T4.10":
            metrics.setdefault(fact.row_id, {})[fact.field] = fact
    for point in report.points:
        rows = [
            row
            for row in metrics.values()
            if row.get("field_1") is not None
            and row["field_1"].status == "known"
            and row["field_1"].text == point.measure_id
        ]
        if len(rows) != 1 or "field_0" not in rows[0]:
            raise OwnerError("identity_mismatch")
        row = rows[0]
        selected = [row["field_0"], row["field_1"], row[report.current_basis_id]]
        if report.prior_basis_id is not None:
            selected.append(row[report.prior_basis_id])
        chosen.update((f.fact_id, f) for f in selected)
    coordinates = [
        {"fact_id": f.fact_id, "table_id": f.table_id, "row_id": f.row_id, "field": f.field}
        for f in sorted(chosen.values(), key=lambda f: (f.table_id, f.row_id, f.field, f.fact_id))
    ]
    grant = {
        "schema_version": "cp1b-upstream-grant/2",
        "consumer_module_id": "CP-1B",
        "step_id": "earnings_delta",
        "producers": [
            {
                "module_id": "CP-1",
                "sha256": producer.content_hash(),
                "coordinates": coordinates,
                "projected_fields": list(_PROJECTED),
            }
        ],
        "raw_source_ids": [],
    }
    return grant, report, producer


def _manifest(binding: OwnerBinding, grant: dict[str, Any], producer: Module) -> dict[str, Any]:
    coordinates = grant["producers"][0]["coordinates"]
    periods = [c for c in coordinates if c["table_id"] == "T4.14"]
    header = {
        "schema_version": "cp1b-access-manifest/1",
        "consumer": {"module_id": "CP-1B", "step_id": "earnings_delta"},
        "producer": {
            "module_id": "CP-1",
            "sha256": producer.content_hash(),
            "status": producer.status,
        },
        "snapshot_sha256": binding.snapshot_sha256,
        "ticket_id": binding.ticket_id,
        "attempt": binding.attempt,
        "grant_sha256": _hash(_canonical(grant).encode()),
        "period_index": {
            "table_id": "T4.14",
            "authorized_complete": True,
            "row_count": len({c["row_id"] for c in periods}),
            "coordinate_count": len(periods),
        },
        "coordinate_count": len(coordinates),
        "projected_fields": list(_PROJECTED),
        "max_page_entries": 20,
        "max_body_bytes": 8192,
    }
    return {
        **header,
        "manifest_sha256": _hash(
            _canonical({"header": header, "coordinates": coordinates}).encode()
        ),
    }


def _safe_fact(fact: Fact) -> dict[str, Any]:
    data = fact.model_dump(mode="json", include=set(_PROJECTED) - {"citation_handles"})
    data["citation_handles"] = [
        {"source_id": c.source_id, "source_sha256": c.source_sha256, "locator": c.locator}
        for c in fact.citations
    ]
    return {key: data[key] for key in _PROJECTED}


def _catalog(grant: dict[str, Any], producer: Module) -> list[dict[str, Any]]:
    facts = {f.fact_id: f for f in producer.facts}
    result = []
    for coordinate in grant["producers"][0]["coordinates"]:
        fact = facts.get(coordinate["fact_id"])
        if fact is None or any(getattr(fact, k) != v for k, v in coordinate.items()):
            raise OwnerError("identity_mismatch")
        result.append(_safe_fact(fact))
    return result


def _page(
    header: dict[str, Any],
    entries: list[dict[str, Any]],
    offset: int,
    count: int,
    token: str | None,
    projection: bool,
) -> dict[str, Any]:
    return {
        "producer": header["producer"],
        **({"projection": "granted_fact_projection"} if projection else {}),
        "grant_sha256": header["grant_sha256"],
        "manifest_sha256": header["manifest_sha256"],
        "coordinate_count": len(entries),
        "offset": offset,
        "entries": entries[offset : offset + count],
        "next_cursor": token,
        "complete": offset + count == len(entries),
    }


def _verify_pages(
    header: dict[str, Any],
    entries: list[dict[str, Any]],
    calls: tuple[OwnerToolCall, ...],
    projection: bool,
) -> tuple[str, ...]:
    """Authenticate issued cursor graphs without replaying private nonce tokens."""
    tool = "read_access_projection" if projection else "read_access_manifest"
    prefix = "projection-cursor:" if projection else "access-cursor:"
    issued: dict[str, int] = {}
    replay: dict[tuple[str | None, int], dict[str, Any]] = {}
    paths: dict[str | None, tuple[str, ...]] = {None: ()}
    complete: tuple[str, ...] = ()
    for call in calls:
        receipt = call.receipt
        if receipt.tool != tool or receipt.status != "ok":
            continue
        args, body = receipt.arguments, receipt.body
        if (
            set(args)
            != {"producer_module_id", "producer_sha256", "manifest_sha256", "cursor", "limit"}
            or args["producer_module_id"] != "CP-1"
            or args["producer_sha256"] != header["producer"]["sha256"]
            or args["manifest_sha256"] != header["manifest_sha256"]
            or type(args["limit"]) is not int
            or not 1 <= args["limit"] <= 20
            or body is None
        ):
            raise OwnerError("identity_mismatch")
        cursor = args["cursor"]
        if cursor is None:
            offset = 0
        elif not isinstance(cursor, str) or cursor not in issued:
            raise OwnerError("identity_mismatch")
        else:
            offset = issued[cursor]
        token = body.get("next_cursor")
        if token is not None and (
            not isinstance(token, str)
            or re.fullmatch(re.escape(prefix) + "[0-9a-f]{64}", token) is None
        ):
            raise OwnerError("identity_mismatch")
        best = 0
        for count in range(1, min(args["limit"], len(entries) - offset) + 1):
            marker = None if offset + count == len(entries) else prefix + "0" * 64
            if (
                len(_canonical(_page(header, entries, offset, count, marker, projection)).encode())
                <= 8192
            ):
                best = count
        if not best or body != _page(header, entries, offset, best, token, projection):
            raise OwnerError("identity_mismatch")
        end = offset + best
        if (token is None) != (end == len(entries)):
            raise OwnerError("identity_mismatch")
        key = (cursor, args["limit"])
        if key in replay and replay[key] != body:
            raise OwnerError("identity_mismatch")
        replay[key] = body
        if token is not None:
            if token in issued and issued[token] != end:
                raise OwnerError("identity_mismatch")
            issued[token] = end
        if cursor in paths:
            path = (*paths[cursor], receipt.call_id)
            if token is not None:
                paths[token] = path
            if end == len(entries):
                complete = path
    return complete


def _owner_session_proof(
    store: Execution,
    session: OwnerSession,
    calls: tuple[OwnerToolCall, ...],
    prior: str,
    current: str,
) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    grant, _, producer = _grant(store, session.binding, prior, current)
    header = _manifest(session.binding, grant, producer)
    if session.normalized_grant_json != _canonical(
        grant
    ) or session.access_manifest_json != _canonical(header):
        raise OwnerError("identity_mismatch")
    if [c.receipt.sequence for c in calls] != list(range(1, len(calls) + 1)):
        raise OwnerError("identity_mismatch")
    for call in calls:
        receipt = call.receipt
        if (
            call.session_id != session.session_id
            or receipt.binding != session.binding
            or receipt.source_evidence != SourceEvidence()
            or receipt.status != "ok"
            and receipt.body is not None
        ):
            raise OwnerError("identity_mismatch")
    manifest_pages = _verify_pages(header, grant["producers"][0]["coordinates"], calls, False)
    projection_pages = _verify_pages(header, _catalog(grant, producer), calls, True)
    permitted = {c["fact_id"] for c in grant["producers"][0]["coordinates"]}
    facts = {f.fact_id: f for f in producer.facts}
    verified: set[str] = set()
    citation_calls = []
    historical = _historical(store, session.binding)
    for call in calls:
        receipt = call.receipt
        if receipt.status != "ok":
            continue
        if receipt.tool in {"read_access_manifest", "read_access_projection"}:
            continue
        args = receipt.arguments
        if (
            args.get("producer_module_id") != "CP-1"
            or args.get("producer_sha256") != producer.content_hash()
        ):
            raise OwnerError("identity_mismatch")
        if receipt.tool == "verify_upstream":
            ids = args.get("fact_ids")
            if (
                set(args) != {"producer_module_id", "producer_sha256", "kind", "fact_ids"}
                or args.get("kind") != "citations"
                or not isinstance(ids, list)
                or not 1 <= len(ids) <= 20
                or any(not isinstance(fid, str) for fid in ids)
                or len(set(ids)) != len(ids)
                or not set(ids) <= permitted
            ):
                raise OwnerError("identity_mismatch")
            fact_ids = tuple(fid for fid in ids if isinstance(fid, str))
            issues = [
                {"code": "fact_citation", "fact_ids": [fid]}
                for fid in fact_ids
                for _ in citation_issues(facts[fid].citations, historical.pack().sources)
            ]
            expected = {
                "producer": header["producer"],
                "grant_sha256": header["grant_sha256"],
                "manifest_sha256": header["manifest_sha256"],
                "kind": "citations",
                "verdict": "invalid" if issues else "valid",
                "issue_count": len(issues),
                "issues": issues,
            }
            if receipt.body != expected or len(_canonical(expected).encode()) > 8192:
                raise OwnerError("identity_mismatch")
            if not issues:
                verified.update(fact_ids)
                citation_calls.append(receipt.call_id)
        elif receipt.tool == "lookup_upstream":
            # Optional legacy lookups are authenticated through the unchanged public
            # tool on a read-only historical session; no opaque cursor is replayed.
            replay = UpstreamTools.from_execution(
                historical, session.binding.ticket_id, "earnings_delta", grants=grant
            ).invoke(receipt.tool, dict(args))
            if (
                replay["status"] != receipt.status
                or replay["body"] != receipt.body
                or replay["error_code"] != receipt.error_code
            ):
                raise OwnerError("identity_mismatch")
        else:
            raise OwnerError("identity_mismatch")
    if verified != permitted:
        citation_calls = []
    return header, manifest_pages, projection_pages, tuple(citation_calls)


def _participation(
    store: Execution,
    binding: OwnerBinding,
    session: OwnerSession,
    reads: tuple[OwnerAccessRead, ...],
    calls: tuple[OwnerToolCall, ...],
    prior: str,
    current: str,
) -> EarningsParticipation:
    ticket_calls = tuple(c for c in calls if c.receipt.binding.ticket_id == binding.ticket_id)
    selected = tuple(c for c in ticket_calls if c.session_id == session.session_id)
    header, manifest, projection, citations = _owner_session_proof(
        store, session, selected, prior, current
    )
    access = tuple(
        r
        for r in reads
        if r.session_id == session.session_id
        and r.binding == binding
        and r.access_manifest_json == session.access_manifest_json
    )
    if session.binding != binding or not access or not manifest or not projection or not citations:
        raise OwnerError("participation_incomplete")
    by_id = {c.receipt.call_id: c.receipt for c in selected}

    def supplies(cid: str, table: str) -> bool:
        body = by_id[cid].body
        entries = body.get("entries") if body is not None else None
        if not isinstance(entries, list):
            raise OwnerError("identity_mismatch")
        return any(isinstance(e, dict) and e.get("table_id") == table for e in entries)

    period_pages = tuple(cid for cid in projection if supplies(cid, "T4.14"))
    metric_pages = tuple(cid for cid in projection if supplies(cid, "T4.10"))
    return EarningsParticipation(
        binding=binding,
        session_id=session.session_id,
        grant_sha256=header["grant_sha256"],
        manifest_sha256=header["manifest_sha256"],
        access_read_sha256=access[-1].content_hash(),
        call_ids=tuple(c.receipt.call_id for c in ticket_calls),
        successful_call_ids=tuple(
            c.receipt.call_id for c in ticket_calls if c.receipt.status == "ok"
        ),
        manifest_call_ids=manifest,
        period_lookup_call_ids=period_pages,
        metric_lookup_call_ids=metric_pages,
        citation_call_ids=citations,
    )


_NUMERIC_ROWS = (
    (
        "T1B.1",
        "Paired earnings results",
        ("prior", "current", "delta", "growth"),
        (
            ("revenue", "Revenue (US$ m)"),
            ("ebitda", "Reported EBITDA (US$ m)"),
            ("adjusted_ebitda", "Adjusted EBITDA (US$ m)"),
            ("ebitda_margin", "EBITDA margin (%; change pp)"),
            ("cfo_reported", "Reported CFO (US$ m)"),
            ("capex", "Signed capex (US$ m)"),
            ("fcf", "Levered FCF (US$ m)"),
        ),
    ),
    (
        "T1B.2",
        "Balance changes",
        ("prior", "current", "delta"),
        (
            ("cash_closing", "Closing cash (US$ m)"),
            ("total_debt", "Total debt (US$ m)"),
            ("net_debt", "Net debt (US$ m)"),
        ),
    ),
)
_ASSESSMENT_ROWS = (
    ("variance.summary", "Numerical comparison"),
    ("drivers", "Driver evidence"),
    ("guidance", "Guidance evidence"),
    ("comparative.prior-year", "Prior-year comparison"),
    ("comparative.trailing-leverage", "Leverage comparison"),
    ("evidence.inputs", "Selected input evidence"),
    ("scope.limitations", "Scope limitations"),
)
_COMMON_LIMITS = (
    "Unaudited consolidated IFRS financials in USD millions; borrower, guarantor and restricted-group perimeters are not established.",
    "No causal-driver evidence is supplied by the selected authorized CP1 inputs.",
    "No management-guidance or operational-KPI evidence is supplied by the selected authorized CP1 inputs.",
    "No FY2024 annual income statement or prior-year quarterly series is supplied.",
)
_CHECKPOINT_LIMIT = "Owner checkpoint only; complete CP5 consumption and selected-run/native rendering are not accepted by this receipt."


def _case_parameters(run: Run) -> tuple[OwnerCaseId, str, str]:
    selected: dict[str, tuple[OwnerCaseId, str, str]] = {
        "slice-cp1b-flat-v1": ("E-QOQ-FLAT", "q3-2025", "q4-2025"),
        "slice-cp1b-no-yoy-v1": ("E-NO-YOY", "fy-2024", "fy-2025"),
        "slice-cp1b-missing-source-v1": ("E-REQUIRED-CP1-MISSING", "q3-2025", "q4-2025"),
    }
    if (
        run.run_id not in selected
        or run.requested_modules != ("CP-1B", "CP-5")
        or run.pathway != "earnings_update"
    ):
        raise OwnerError("identity_mismatch")
    return selected[run.run_id]


def _own_limits(gap: bool) -> tuple[str, ...]:
    return (
        *_COMMON_LIMITS,
        "No year-on-year earnings comparison or broader nonzero earnings qualification."
        if gap
        else "Bounded flat sequential earnings comparison only; no broader nonzero earnings qualification.",
        _CHECKPOINT_LIMIT,
        "Requested FY2024 comparison basis is absent; current FY2025 values remain known. Opening-2024 balance data is not a substituted income comparator."
        if gap
        else "Q3 trailing leverage comparison is unavailable; current Q4 standalone leverage remains valid.",
    )


def _reference(producer_sha256: str, fact: Fact) -> FactReference:
    return FactReference(
        producer_module_id="CP-1",
        producer_sha256=producer_sha256,
        fact_id=fact.fact_id,
        table_id=fact.table_id,
        row_id=fact.row_id,
        field=fact.field,
    )


def _operands(producer: Module, report: EarningsDeltaReport) -> tuple[OperandLineage, ...]:
    facts = {f.fact_id: f for f in producer.facts}
    producer_sha256 = producer.content_hash()

    def operand(fid: str, pid: str, basis: str) -> OperandReference:
        fact = facts[fid]
        if fact.period is None or fact.basis is None:
            raise OwnerError("identity_mismatch")
        return OperandReference(
            fact=_reference(producer_sha256, fact),
            period_id=pid,
            basis_id=basis,
            source_period=fact.period,
            source_basis=fact.basis,
            fact_sha256=fact.content_hash(),
            citation_handles=tuple(
                CitationHandle(
                    source_id=c.source_id, source_sha256=c.source_sha256, locator=c.locator
                )
                for c in fact.citations
            ),
        )

    return tuple(
        OperandLineage(
            measure_id=p.measure_id,
            prior=operand(p.prior_fact_id, report.prior_period_id, report.prior_basis_id)
            if p.prior_fact_id is not None and report.prior_basis_id is not None
            else None,
            current=operand(p.current_fact_id, report.current_period_id, report.current_basis_id),
            companions=tuple(
                _reference(producer_sha256, facts[fid]) for fid in p.companion_fact_ids
            ),
        )
        for p in report.points
    )


def _citations(facts: tuple[Fact, ...]) -> tuple[Citation, ...]:
    return tuple(dict.fromkeys(c for f in facts for c in f.citations))


def _period_heading(producer: Module, pid: str, role: str, absent: bool) -> str:
    if absent:
        return f"Requested {pid} (not supplied)"
    rows: dict[str, dict[str, Fact]] = {}
    for fact in producer.facts:
        if fact.table_id == "T4.14":
            rows.setdefault(fact.row_id, {})[fact.field] = fact
    selected = [row for row in rows.values() if row["period_id"].text == pid]
    if len(selected) != 1:
        raise OwnerError("identity_mismatch")
    start = date.fromisoformat(selected[0]["start_date"].text or "")
    end = date.fromisoformat(selected[0]["end_date"].text or "")
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    label = f"{start.day} {months[start.month - 1]}–{end.day} {months[end.month - 1]} {end.year}"
    return f"{role.title()} {pid} ({label})"


def _compose(
    producer: Module,
    report: EarningsDeltaReport,
    operands: tuple[OperandLineage, ...],
    review: EarningsDeltaReview,
    participation: EarningsParticipation,
    attempt: Attempt,
    run: Run,
) -> Module:
    gap = report.prior_basis_id is None
    own_limits = _own_limits(gap)
    facts_by_id = {f.fact_id: f for f in producer.facts}
    points = {p.measure_id: p for p in report.points}
    lineage = {p.measure_id: p for p in operands}
    pair = f"{report.prior_period_id}->{report.current_period_id}"
    headings = {
        "prior": _period_heading(producer, report.prior_period_id, "prior", gap),
        "current": _period_heading(producer, report.current_period_id, "current", False),
        "delta": "Change (native unit; margin pp)",
        "growth": "Growth (%)",
    }
    table_limit = (
        "Missing selected FY2024 comparison basis; current FY2025 values remain known; "
        "Opening-2024 balance data exists; this is not a claim that balance data is unavailable; "
        "Opening-2024 is not silently aliased to requested FY2024 income basis; "
        "Whole-million monetary display; exact canonical values remain in facts/passports"
        if gap
        else "Whole-million monetary display; exact canonical values remain in facts/passports; "
        "Quarter earnings use own-period values; leverage uses its selected trailing basis"
    )
    facts: list[Fact] = []
    tables = []
    for table_id, title, columns, measures in _NUMERIC_ROWS:
        rows = []
        for measure, label in measures:
            point = points[measure]
            prior = facts_by_id.get(point.prior_fact_id) if point.prior_fact_id else None
            current = facts_by_id[point.current_fact_id]
            ids = []
            for field in columns:
                fid = f"cp1b:{table_id}:{measure}:{field}"
                common: dict[str, Any] = {
                    "fact_id": fid,
                    "table_id": table_id,
                    "row_id": measure,
                    "field": field,
                    "label": f"{label} · {field}",
                    "decimals": None,
                }
                if field in {"prior", "current"}:
                    original = prior if field == "prior" else current
                    if original is None:
                        fact = Fact(
                            **common,
                            amount=None,
                            status="missing",
                            unit=point.unit,
                            currency=point.currency,
                            scale=point.scale,
                            period=report.prior_period_id,
                            limitation="COMPARATIVE_NOT_SUPPLIED",
                        )
                    else:
                        fact = original.model_copy(
                            update={
                                **common,
                                "period": report.prior_period_id
                                if field == "prior"
                                else report.current_period_id,
                                "calculation_id": None,
                                "formula": None,
                            }
                        )
                        fact = Fact.model_validate_json(fact.model_dump_json())
                else:
                    growth = field == "growth"
                    status = point.growth_status if growth else point.delta_status
                    nongrowth = growth and status == "not_applicable"
                    unit = (
                        "PERCENT"
                        if growth
                        else "pp"
                        if point.delta_unit == "PERCENTAGE_POINTS"
                        else point.delta_unit
                    )
                    formula = (
                        "(current - prior) / prior"
                        if growth
                        else "100 * (current - prior)"
                        if measure == "ebitda_margin"
                        else "current - prior"
                    )
                    fact = Fact(
                        **common,
                        amount=point.growth if growth else point.delta,
                        status=status,
                        unit=unit,
                        currency=None if growth or unit == "pp" else point.currency,
                        scale=Decimal(1) if growth or unit == "pp" else point.scale,
                        period=pair,
                        basis=_canonical(lineage[measure].model_dump(mode="json")),
                        citations=_citations(tuple(f for f in (prior, current) if f is not None)),
                        value_class="calculated",
                        calculation_id=None
                        if nongrowth
                        else f"cp1b-calc:{report.prior_period_id}:{report.current_period_id}:{measure}:{field}",
                        calculation_status=status,
                        formula=None if nongrowth else formula,
                        limitation="GROWTH_NOT_APPLICABLE" if nongrowth else point.reason,
                    )
                facts.append(fact)
                ids.append(fid)
            rows.append(TableRow(row_id=measure, label=label, fact_ids=tuple(ids)))
        tables.append(
            ReportTable(
                table_id=table_id,
                title=title,
                row_header="Measure",
                columns=tuple(TableColumn(field=f, label=headings[f]) for f in columns),
                rows=tuple(rows),
                limitation=table_limit,
            )
        )
    evidence = {
        "producer_module_id": "CP-1",
        "producer_sha256": producer.content_hash(),
        "prior_period_id": report.prior_period_id,
        "current_period_id": report.current_period_id,
        "prior_basis_id": report.prior_basis_id,
        "current_basis_id": report.current_basis_id,
        "operands": [o.model_dump(mode="json") for o in operands],
    }
    all_selected = tuple(
        facts_by_id[fid]
        for p in report.points
        for fid in (p.prior_fact_id, p.current_fact_id, *p.companion_fact_ids)
        if fid is not None
    )
    shared_citations = _citations(all_selected)
    assessments = (
        (
            "missing" if gap else "known",
            None
            if gap
            else "The selected q3-2025 to q4-2025 own-quarter earnings comparison is flat; no causal-driver inference is supported.",
            "COMPARATIVE_NOT_SUPPLIED: requested FY2024 comparison basis is absent; current FY2025 values remain known."
            if gap
            else None,
            "analyst_judgment",
            shared_citations,
        ),
        (
            "missing",
            None,
            "DRIVER_EVIDENCE_NOT_SUPPLIED: no price, volume, FX or other causal-driver evidence is supplied by the selected authorized CP1 inputs.",
            "analyst_judgment",
            (),
        ),
        (
            "missing",
            None,
            "GUIDANCE_NOT_SUPPLIED: no management-guidance evidence is supplied by the selected authorized CP1 inputs.",
            "analyst_judgment",
            (),
        ),
        (
            "missing",
            None,
            "COMPARATIVE_NOT_SUPPLIED: no FY2024 annual income statement or prior-year quarterly series is supplied.",
            "analyst_judgment",
            shared_citations,
        ),
        (
            "missing",
            None,
            "COMPARATIVE_NOT_SUPPLIED: requested FY2024 leverage comparison basis is absent; current FY2025 leverage remains valid."
            if gap
            else "Four complete contiguous quarters are unavailable for Q3 trailing leverage; current Q4 standalone leverage remains valid.",
            "analyst_judgment",
            shared_citations,
        ),
        ("known", _canonical(evidence), None, "normalized", shared_citations),
        ("known", "\n".join(own_limits), None, "normalized", ()),
    )
    rows = []
    for (rid, label), (assessment_status, text, limitation, value_class, citations) in zip(
        _ASSESSMENT_ROWS, assessments, strict=True
    ):
        fid = f"cp1b:T1B.3:{rid}:assessment"
        facts.append(
            _parse(
                Fact,
                {
                    "fact_id": fid,
                    "label": label,
                    "table_id": "T1B.3",
                    "row_id": rid,
                    "field": "assessment",
                    "status": assessment_status,
                    "text": text,
                    "limitation": limitation,
                    "period": pair,
                    "value_class": value_class,
                    "citations": [c.model_dump(mode="json") for c in citations],
                },
            )
        )
        rows.append(TableRow(row_id=rid, label=label, fact_ids=(fid,)))
    tables.append(
        ReportTable(
            table_id="T1B.3",
            title="Evidence and analytical gaps",
            row_header="Assessment",
            columns=(TableColumn(field="assessment", label="Assessment"),),
            rows=tuple(rows),
        )
    )
    text = (
        "Current earnings observations: {cp1b:T1B.1:revenue:current|MILLIONS} {cp1b:T1B.1:ebitda:current|MILLIONS}. Requested prior income comparison is unavailable [cp1b:T1B.1:revenue:prior] [cp1b:T1B.1:revenue:delta] [cp1b:T1B.1:revenue:growth]."
        if gap
        else "Flat sequential earnings comparison: {cp1b:T1B.1:revenue:delta|MILLIONS} {cp1b:T1B.1:ebitda:delta|MILLIONS} {cp1b:T1B.1:adjusted_ebitda:delta|MILLIONS}. Current balance observations: {cp1b:T1B.2:cash_closing:current|MILLIONS} {cp1b:T1B.2:total_debt:current|MILLIONS} {cp1b:T1B.2:net_debt:current|MILLIONS}."
    )
    reference_ids = tuple(run.text for run in tokenize(text) if run.kind != "text")
    owned = {f.fact_id: f for f in facts}
    claim = Claim(
        claim_id="cp1b-comparison",
        text=text,
        citations=_citations(tuple(owned[fid] for fid in reference_ids)),
        limitation="COMPARATIVE_NOT_SUPPLIED: requested FY2024 income and comparison basis are absent; current FY2025 values remain known. Opening-2024 balance data is not an income comparator."
        if gap
        else "Flat sequential earnings only; causal drivers, management guidance and prior-year income are not supplied. The prior trailing-leverage comparison is unavailable.",
    )
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        method_version=run.method_version,
        module_id="CP-1B",
        status="candidate",
        attempt=attempt.number,
        inputs=(
            *attempt.inputs,
            Input(input_id="earnings-review", sha256=review.content_hash()),
            Input(input_id="earnings-participation", sha256=participation.content_hash()),
        ),
        facts=tuple(facts),
        tables=tuple(tables),
        claims=(claim,),
        limitations=own_limits,
    )


def _owner_stage(store: Execution, envelope: OwnerSubmissionEnvelope) -> EarningsOwnerStage:
    historical = _historical(store, envelope.binding)
    snapshot = historical.read()
    _, prior, current = _case_parameters(snapshot.run)
    review = envelope.review
    try:
        raw_review = EarningsDeltaReview.model_validate_json(
            _raw(store, envelope.raw_review_sha256)
        )
    except ValidationError:
        # The one place the actor's own review text is parsed: charged to the actor.
        raise OwnerError("validation_failed") from None
    _, view = _full_cp1(store, envelope.binding)
    build_earnings_delta(view, review.prior_period_id, review.current_period_id)
    if raw_review != review or (review.prior_period_id, review.current_period_id) != (
        prior,
        current,
    ):
        raise OwnerError("validation_failed")
    sessions = _records(store, "owner-sessions", OwnerSession)
    chosen = [s for s in sessions if s.session_id == envelope.participation.session_id]
    if len(chosen) != 1:
        raise OwnerError("identity_mismatch")
    all_calls = tuple(
        sorted(_records(store, "owner-calls", OwnerToolCall), key=lambda c: c.ordinal)
    )
    intents = [
        i
        for i in _records(store, "intents", SubmissionIntent)
        if i.binding.stored_payload_sha256 == envelope.content_hash()
        and i.binding.binding == envelope.binding
        and i.binding.owner_session_id == envelope.participation.session_id
        and i.binding.participation_sha256 == envelope.participation.content_hash()
    ]
    if len(intents) != 1:
        raise OwnerError("identity_mismatch")
    bound = intents[0].binding
    if (
        envelope.participation.call_ids != bound.call_ids
        or envelope.participation.successful_call_ids != bound.successful_call_ids
    ):
        raise OwnerError("identity_mismatch")
    reads_by_hash = {r.content_hash(): r for r in _records(store, "owner-reads", OwnerAccessRead)}
    captured_reads = tuple(reads_by_hash[digest] for digest in bound.input_read_hashes)
    ticket_calls = tuple(
        c for c in all_calls if c.receipt.binding.ticket_id == envelope.binding.ticket_id
    )
    prefix = ticket_calls[: len(envelope.participation.call_ids)]
    actual = _participation(
        store,
        envelope.binding,
        chosen[0],
        captured_reads,
        prefix,
        prior,
        current,
    )
    if actual != envelope.participation:
        raise OwnerError("participation_incomplete")
    _, report, producer = _grant(store, envelope.binding, prior, current)
    selections = tuple(
        MeasureSelection(
            measure_id=p.measure_id,
            prior_fact_id=p.prior_fact_id,
            current_fact_id=p.current_fact_id,
            companion_fact_ids=p.companion_fact_ids,
        )
        for p in report.points
    )
    if review.selections != selections or review.comparison_assessment != (
        "comparative_not_supplied" if report.prior_basis_id is None else "flat_sequential"
    ):
        raise OwnerError("validation_failed")
    operands = _operands(producer, report)
    attempt = next(a for a in snapshot.attempts if a.ticket_id == envelope.binding.ticket_id)
    candidate = _compose(producer, report, operands, review, actual, attempt, snapshot.run)
    return EarningsOwnerStage(
        review_sha256=review.content_hash(),
        participation_sha256=actual.content_hash(),
        report=EarningsReportRecord.model_validate(asdict(report)),
        operands=operands,
        candidate=candidate,
    )


def _stage_validation(store: Execution, envelope: OwnerSubmissionEnvelope) -> StepValidation:
    try:
        stage = _owner_stage(store, envelope)
    except OwnerError as error:
        return StepValidation(issues=(error.code,))
    except ValueError as error:
        # A pydantic ValidationError is a ValueError outside this set, so B1's own
        # composition defects propagate; only the actor review parse is charged.
        if str(error) not in {
            "incompatible_periods",
            "incomplete_register",
            "invalid_source_view",
            "incompatible_dimensions",
            "ambiguous_coordinate",
            "invalid_fact",
        }:
            raise
        return StepValidation(issues=(str(error),))
    return StepValidation(output=stage.model_dump_json())


def submit_earnings_delta(store: Execution, ticket_id: str, payload: str) -> Attempt:
    """Submit the host's durable envelope and settle only its rederived candidate."""
    envelope = OwnerSubmissionEnvelope.model_validate_json(payload)
    setup, _ = _setup(store, _CASE_MANIFEST)
    _verify_open_history(store, setup)
    attempts = [a for a in store.read().attempts if a.ticket_id == ticket_id]
    if len(attempts) != 1 or attempts[0].module_id != "CP-1B" or attempts[0].status != "pending":
        raise OwnerError("stale_binding")
    attempt = attempts[0]
    if envelope.binding.ticket_id != ticket_id:
        raise OwnerError("identity_mismatch")
    if _raw(store, _hash(payload.encode())) != payload.encode():
        raise OwnerError("identity_mismatch")
    intents = _records(store, "intents", SubmissionIntent)
    if not any(
        i.binding.binding == envelope.binding
        and i.binding.stored_payload_sha256 == _hash(payload.encode())
        and i.binding.raw_payload_sha256 == envelope.raw_review_sha256
        and i.binding.participation_sha256 == envelope.participation.content_hash()
        for i in intents
    ):
        raise OwnerError("identity_mismatch")
    if attempt.steps and attempt.steps[0].payload_sha256 != _hash(payload.encode()):
        raise OwnerError("identity_mismatch")
    if attempt.steps and attempt.steps[0].status == "valid":
        output_hash = attempt.steps[0].output_sha256
        if output_hash is None:
            raise OwnerError("identity_mismatch")
        with _stored_read():
            retained = store.step_output(output_hash).encode()
        if _stored_bytes(store, "stages", output_hash) != retained:
            raise OwnerError("identity_mismatch")

    def validation(_pack: PreparedPack, _attempt: Attempt) -> StepValidation:
        result = _stage_validation(store, envelope)
        if not result.issues:
            _retain(store, "stages", EarningsOwnerStage.model_validate_json(result.output or ""))
        return result

    if not attempt.steps or attempt.steps[0].status == "pending":
        attempt = store.submit_step(
            ticket_id, "CP-1B", ("earnings_delta",), "earnings_delta", payload, validation
        )
    if attempt.status == "finished":
        return attempt
    with _stored_read():
        pack = store.pack()
    outcome = validation(pack, attempt)
    if outcome.issues or not outcome.retained_as(attempt.steps[0]):
        raise OwnerError("identity_mismatch")
    stage = EarningsOwnerStage.model_validate_json(outcome.output or "")
    _payload(store, stage.candidate.model_dump_json().encode())
    return store.finish(
        ticket_id,
        stage.candidate.model_dump_json(),
        lambda supplied: () if supplied == stage.candidate else ("validation_failed",),
    )


def _foundation_calls(store: Execution, binding: FinancialBinding) -> tuple[FinancialCall, ...]:
    return tuple(
        sorted(
            (c for c in _records(store, "foundation-calls", FinancialCall) if c.binding == binding),
            key=lambda c: c.sequence,
        )
    )


def _source_session(store: Execution, binding: FinancialBinding) -> SourceSession:
    historical = _historical(store, binding)
    session = SourceSession.from_execution(historical, binding.ticket_id, binding.step_id)
    for sequence, call in enumerate(_foundation_calls(store, binding), 1):
        if call.sequence != sequence:
            raise OwnerError("identity_mismatch")
        replay = session.invoke(call.tool, call.arguments)
        replay["call_id"] = call.call_id
        if _parse(FinancialCall, replay) != call:
            raise OwnerError("identity_mismatch")
    return session


def _prepare_bound(
    store: Execution,
    binding: FinancialBinding | OwnerBinding,
    payload: str,
    session: OwnerSession | None = None,
) -> tuple[BoundSubmission, tuple[str, ...]]:
    if isinstance(binding, OwnerBinding):
        if session is None:
            raise OwnerError("not_permitted")
        actual = [
            s
            for s in _records(store, "owner-sessions", OwnerSession)
            if s.session_id == session.session_id
        ]
        if len(actual) != 1 or actual[0] != session or session.binding != binding:
            raise OwnerError("identity_mismatch")
        _, prior, current = _case_parameters(_historical(store, binding).read().run)
        _owner_session_proof(store, session, (), prior, current)
    raw_hash = _payload(store, payload.encode())
    if isinstance(binding, FinancialBinding):
        historical = _historical(store, binding)
        calls = _foundation_calls(store, binding)
        evidence = calls[-1].source_evidence if calls else SourceEvidence()
        if binding.step_id in _SOURCE_PHASES:
            attached = _source_session(store, binding).bind_submission(payload)
            generated_ids = attached.get("call_ids")
            if (
                not isinstance(generated_ids, list)
                or len(generated_ids) != len(calls)
                or len(set(generated_ids)) != len(generated_ids)
                or attached.get("successful_call_ids")
                != [generated_ids[index] for index, call in enumerate(calls) if call.status == "ok"]
            ):
                raise OwnerError("identity_mismatch")
            # Public replay generates new UUIDs. Only these UUID positions may
            # be replaced; every argument/body/status/evidence field was checked.
            attached = {
                **attached,
                "call_ids": [c.call_id for c in calls],
                "successful_call_ids": [c.call_id for c in calls if c.status == "ok"],
            }
            expected = {
                "schema_version": "submission-binding/1",
                "binding": binding.model_dump(mode="json"),
                "payload_sha256": raw_hash,
                "successful_call_ids": [c.call_id for c in calls if c.status == "ok"],
                "call_ids": [c.call_id for c in calls],
                "source_evidence": evidence.model_dump(mode="json"),
            }
            if attached != expected:
                raise OwnerError("identity_mismatch")
        filled, normalized, paths, kinds = _filled(historical, binding, payload)
        stored_hash = _payload(store, filled.encode())
        issues = _source_issues(historical, binding, filled, evidence, calls)
        reads = tuple(
            sorted(
                (r for r in _records(store, "foundation-reads", InputRead) if r.binding == binding),
                key=lambda r: r.sequence,
            )
        )
        if binding.step_id not in _SOURCE_PHASES and not reads:
            issues = (*issues, "participation_incomplete")
        for sequence, read in enumerate(reads, 1):
            if read.sequence != sequence or (read.inputs_sha256, read.body) != _projection(
                store, binding
            ):
                raise OwnerError("identity_mismatch")
        try:
            canonical = _SCHEMAS[binding.step_id].model_validate_json(filled).content_hash()
        except ValidationError:
            canonical = None
        return BoundSubmission(
            binding=binding,
            raw_payload_sha256=raw_hash,
            stored_payload_sha256=stored_hash,
            canonical_review_sha256=canonical,
            call_ids=tuple(c.call_id for c in calls),
            successful_call_ids=tuple(c.call_id for c in calls if c.status == "ok"),
            source_evidence=evidence,
            input_read_hashes=tuple(r.content_hash() for r in reads),
            participation_sha256=None,
            owner_session_id=None,
            normalization_paths=normalized,
            prefilled_paths=paths,
            prefilled_kinds=kinds,
        ), issues
    owner_calls = tuple(
        sorted(
            (
                c
                for c in _records(store, "owner-calls", OwnerToolCall)
                if c.receipt.binding.ticket_id == binding.ticket_id
            ),
            key=lambda c: c.ordinal,
        )
    )
    session_order = {
        s.session_id: s.index
        for s in _records(store, "owner-sessions", OwnerSession)
        if s.binding.ticket_id == binding.ticket_id
    }
    owner_reads = tuple(
        sorted(
            (
                r
                for r in _records(store, "owner-reads", OwnerAccessRead)
                if r.binding.ticket_id == binding.ticket_id
            ),
            key=lambda r: (_known(session_order, r.session_id), r.sequence),
        )
    )
    try:
        review = EarningsDeltaReview.model_validate_json(payload)
    except ValidationError:
        review = None
    participation = None
    issues = () if review is not None else ("bad_arguments",)
    if review is not None:
        _, prior, current = _case_parameters(_historical(store, binding).read().run)
        if session is None:
            issues = ("participation_incomplete",)
        else:
            try:
                participation = _participation(
                    store, binding, session, owner_reads, owner_calls, prior, current
                )
            except OwnerError as error:
                if error.code not in {
                    "participation_incomplete",
                    "identity_mismatch",
                    "stale_binding",
                }:
                    raise
                issues = (error.code,)
    if participation is not None and review is not None:
        _retain(store, "participations", participation)
        envelope = OwnerSubmissionEnvelope(
            binding=binding, raw_review_sha256=raw_hash, review=review, participation=participation
        )
        stored_hash = _payload(store, envelope.model_dump_json().encode())
    else:
        stored_hash = raw_hash
    return BoundSubmission(
        binding=binding,
        raw_payload_sha256=raw_hash,
        stored_payload_sha256=stored_hash,
        canonical_review_sha256=review.content_hash() if review is not None else None,
        call_ids=tuple(c.receipt.call_id for c in owner_calls),
        successful_call_ids=tuple(
            c.receipt.call_id for c in owner_calls if c.receipt.status == "ok"
        ),
        source_evidence=SourceEvidence(),
        input_read_hashes=tuple(r.content_hash() for r in owner_reads),
        participation_sha256=participation.content_hash() if participation else None,
        owner_session_id=session.session_id if session is not None else None,
        normalization_paths=(),
        prefilled_paths=(),
        prefilled_kinds=(),
    ), issues


def _intent_session(store: Execution, intent: SubmissionIntent) -> OwnerSession | None:
    if not isinstance(intent.binding.binding, OwnerBinding):
        return None
    sessions = [
        s
        for s in _records(store, "owner-sessions", OwnerSession)
        if s.session_id == intent.binding.owner_session_id
    ]
    if len(sessions) != 1 or sessions[0].binding != intent.binding.binding:
        raise OwnerError("identity_mismatch")
    if intent.binding.participation_sha256 is not None:
        parts = [
            p
            for p in _records(store, "participations", EarningsParticipation)
            if p.content_hash() == intent.binding.participation_sha256
        ]
        if len(parts) != 1:
            raise OwnerError("identity_mismatch")
        if parts[0].session_id != intent.binding.owner_session_id:
            raise OwnerError("identity_mismatch")
    _, prior, current = _case_parameters(_historical(store, sessions[0].binding).read().run)
    _owner_session_proof(store, sessions[0], (), prior, current)
    return sessions[0]


def _unresolved(store: Execution) -> tuple[SubmissionIntent, ...]:
    outcomes = _records(store, "outcomes", SubmissionOutcome)
    by_intent = [o.intent_sha256 for o in outcomes]
    if len(set(by_intent)) != len(by_intent):
        raise OwnerError("identity_mismatch")
    intents = tuple(sorted(_records(store, "intents", SubmissionIntent), key=lambda i: i.index))
    if [i.index for i in intents] != list(range(1, len(intents) + 1)) or not set(by_intent) <= {
        i.content_hash() for i in intents
    }:
        raise OwnerError("identity_mismatch")
    pending = tuple(i for i in intents if i.content_hash() not in by_intent)
    if len(pending) > 1 or pending and pending[0] != intents[-1]:
        raise OwnerError("identity_mismatch")
    return pending


def _new_steps(before: ExecutionSnapshot, attempt: Attempt) -> list[StepSubmission]:
    """Steps of `attempt` that `before` does not already account for.

    Steps present in the before-snapshot belong to earlier intents. Subtracting
    them as a multiset keeps an identical resubmission a distinct journal step,
    so it is credited to the intent that produced it and to no other.
    """
    remaining = Counter(
        s.content_hash()
        for a in before.attempts
        if a.ticket_id == attempt.ticket_id
        for s in (*a.steps, *a.step_repairs)
    )
    result = []
    for step in (*attempt.steps, *attempt.step_repairs):
        digest = step.content_hash()
        if remaining[digest] > 0:
            remaining[digest] -= 1
        else:
            result.append(step)
    return result


def _complete_intent(store: Execution, intent: SubmissionIntent) -> SubmissionOutcome:
    bound = intent.binding
    payload = _text(store, bound.raw_payload_sha256)
    rebound, issues = _prepare_bound(store, bound.binding, payload, _intent_session(store, intent))
    if rebound != bound or intent.snapshot_before_sha256 != bound.binding.snapshot_sha256:
        raise OwnerError("identity_mismatch")
    before = _snapshot(store, intent.snapshot_before_sha256)
    current = store.read()
    attempt = next((a for a in current.attempts if a.ticket_id == bound.binding.ticket_id), None)
    if attempt is None:
        raise OwnerError("identity_mismatch")

    def produced(candidate_attempt: Attempt) -> list[StepSubmission]:
        return [
            s
            for s in _new_steps(before, candidate_attempt)
            if s.step_id == bound.binding.step_id
            and s.payload_sha256 == bound.stored_payload_sha256
        ]

    matching = produced(attempt)
    if issues:
        if matching or current.content_hash() != before.content_hash():
            raise OwnerError("identity_mismatch")
        outcome = SubmissionOutcome(
            intent_sha256=intent.content_hash(),
            disposition="refused",
            issues=issues,
            snapshot_after_sha256=current.content_hash(),
            step_sha256=None,
            step_output_sha256=None,
            candidate_sha256=None,
            result_sha256=None,
        )
        _retain(store, "outcomes", outcome)
        return outcome
    terminal_step = bound.binding.step_id in {"source_readiness", "quality", "earnings_delta"}
    needs_submit = (
        not matching
        or matching[-1].status == "pending"
        or terminal_step
        and attempt.status == "pending"
    )
    if needs_submit:
        if attempt.status != "pending":
            raise OwnerError("identity_mismatch")
        if isinstance(bound.binding, OwnerBinding):
            attempt = submit_earnings_delta(
                store, bound.binding.ticket_id, _text(store, bound.stored_payload_sha256)
            )
        elif bound.binding.step_id == "source_readiness":
            attempt = submit_cp0_review(
                store, bound.binding.ticket_id, _text(store, bound.stored_payload_sha256)
            )
        else:
            submitted = submit_model_payload(
                store, bound.binding.ticket_id, bound.binding.step_id, payload
            )
            if (
                submitted.payload,
                submitted.nulls_resolved,
                submitted.prefilled,
                submitted.prefilled_kinds,
            ) != (
                _text(store, bound.stored_payload_sha256),
                bound.normalization_paths,
                bound.prefilled_paths,
                bound.prefilled_kinds,
            ):
                raise OwnerError("identity_mismatch")
            attempt = submitted.journal
        current = store.read()
        matching = produced(attempt)
    if len(matching) != 1 or matching[0].status == "pending":
        raise OwnerError("identity_mismatch")
    step = matching[0]
    if attempt.payload_sha256 is not None:
        with _stored_read():
            candidate_text = store.payload(attempt.payload_sha256)
        _payload(store, candidate_text.encode())
    outcome = SubmissionOutcome(
        intent_sha256=intent.content_hash(),
        disposition="valid" if step.status == "valid" and not attempt.issues else "invalid",
        issues=step.issues or attempt.issues,
        snapshot_after_sha256=current.content_hash(),
        step_sha256=step.content_hash(),
        step_output_sha256=step.output_sha256,
        candidate_sha256=attempt.payload_sha256,
        result_sha256=attempt.result_sha256,
    )
    _retain(store, "outcomes", outcome)
    return outcome


def _preflight(producer: Module, prior: str, current: str) -> None:
    view = ModuleView(
        module_id="CP-1",
        title="Financials",
        aliases=(),
        status=producer.status,
        artifact_sha256=producer.content_hash(),
        facts=producer.facts,
        tables=producer.tables,
        claims=producer.claims,
        limitations=producer.limitations,
    )
    report = build_earnings_delta(view, prior, current)
    bases = {report.current_basis_id}
    if report.prior_basis_id is not None:
        bases.add(report.prior_basis_id)
    rows = {
        f.row_id for f in producer.facts if f.fact_id in {p.current_fact_id for p in report.points}
    }
    chosen = tuple(
        f
        for f in producer.facts
        if f.table_id == "T4.14"
        or f.table_id == "T4.10"
        and f.row_id in rows
        and f.field in {*bases, "field_0", "field_1"}
    )
    # Fixed-width digest/cursor sentinels are exclusively a byte-size calculation,
    # never a grant, bound producer, recorded tool call or settlement authority.
    header = {
        "producer": {
            "module_id": "CP-1",
            "sha256": producer.content_hash(),
            "status": producer.status,
        },
        "grant_sha256": "0" * 64,
        "manifest_sha256": "0" * 64,
    }
    if len(chosen) * 3 > MAX_OWNER_CALLS:
        raise OwnerError("transport_limit")
    entries = [_safe_fact(f) for f in chosen]
    for offset in range(len(entries)):
        token = None if offset + 1 == len(entries) else "projection-cursor:" + "0" * 64
        if len(_canonical(_page(header, entries, offset, 1, token, True)).encode()) > 8192:
            raise OwnerError("transport_limit")


class _WriteProposal(BaseException):
    def __init__(self, snapshot: ExecutionSnapshot) -> None:
        self.snapshot = snapshot


class _MutationProbe(_FrozenExecution):
    """Re-enter public core APIs but forbid every actual write and lock mutation."""

    @contextmanager
    def _locked(self) -> Iterator[None]:
        yield

    def _store(self, text: str) -> str:
        raw = text.encode()
        digest = _hash(raw)
        if self._load(digest) != raw:
            raise OwnerError("identity_mismatch")
        return digest

    def _write(self, snapshot: ExecutionSnapshot) -> None:
        raise _WriteProposal(snapshot)


def _propose_owner(probe: _MutationProbe, bound: BoundSubmission) -> None:
    envelope = OwnerSubmissionEnvelope.model_validate_json(_raw(probe, bound.stored_payload_sha256))
    attempt = next(a for a in probe.read().attempts if a.ticket_id == bound.binding.ticket_id)

    def validate(_pack: PreparedPack, _attempt: Attempt) -> StepValidation:
        return _stage_validation(probe, envelope)

    if not attempt.steps or attempt.steps[0].status == "pending":
        attempt = probe.submit_step(
            attempt.ticket_id,
            "CP-1B",
            ("earnings_delta",),
            "earnings_delta",
            _text(probe, bound.stored_payload_sha256),
            validate,
        )
    if attempt.status == "finished":
        return
    outcome = validate(probe.pack(), attempt)
    if outcome.issues or not outcome.retained_as(attempt.steps[0]):
        raise OwnerError("identity_mismatch")
    candidate = EarningsOwnerStage.model_validate_json(outcome.output or "").candidate
    probe.finish(
        attempt.ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("validation_failed",),
    )


def _propose_submission(
    store: Execution, before: ExecutionSnapshot, bound: BoundSubmission
) -> ExecutionSnapshot:
    attempt = next((a for a in before.attempts if a.ticket_id == bound.binding.ticket_id), None)
    if attempt is None or attempt.status != "pending":
        # The intent was bound to a pending attempt, and its outcome is written before
        # any later begin; a finished or absent ticket here means a lost outcome record.
        raise OwnerError("identity_mismatch")
    probe = _MutationProbe(store, before)
    try:
        if isinstance(bound.binding, OwnerBinding):
            _propose_owner(probe, bound)
        elif bound.binding.step_id == "source_readiness":
            submit_cp0_review(
                probe, bound.binding.ticket_id, _text(store, bound.stored_payload_sha256)
            )
        else:
            submit_model_payload(
                probe,
                bound.binding.ticket_id,
                bound.binding.step_id,
                _text(store, bound.raw_payload_sha256),
            )
    except _WriteProposal as proposal:
        return proposal.snapshot
    raise OwnerError("identity_mismatch")


def _chain(store: Execution, anchor: str) -> tuple[ExecutionSnapshot, ...]:
    chain: list[ExecutionSnapshot] = []
    seen = set()
    digest: str | None = anchor
    while digest is not None:
        if digest in seen or len(chain) >= MAX_AUDIT:
            raise OwnerError("identity_mismatch")
        seen.add(digest)
        snapshot = _snapshot(store, digest)
        chain.append(snapshot)
        digest = snapshot.parent
    chain.reverse()
    if any(s.run != chain[0].run or s.pack_sha256 != chain[0].pack_sha256 for s in chain):
        raise OwnerError("identity_mismatch")
    return tuple(chain)


def _verify_begin(store: Execution, record: BeginRecord) -> None:
    before = _snapshot(store, record.snapshot_before_sha256)
    if any(a.status == "pending" for a in before.attempts):
        # `_begin` only ever runs with no pending attempt (the core refuses otherwise
        # and nothing is recorded), so a begin recorded from such a snapshot is forged.
        raise OwnerError("identity_mismatch")
    if record.error_code is not None:
        if (
            record.error_code != "not_authorized"
            or record.module_id != "CP-1"
            or record.ticket_id is not None
            or record.attempt is not None
        ):
            raise OwnerError("identity_mismatch")
        try:
            current_inputs(before, record.module_id)
        except NotAuthorized:
            if record.snapshot_after_sha256 == record.snapshot_before_sha256:
                return
        except ValueError as error:
            # The core refuses with a ValueError (execution.py:210-213); a refusal other
            # than NotAuthorized contradicts the recorded `not_authorized` begin.
            raise OwnerError("identity_mismatch") from error
        raise OwnerError("identity_mismatch")
    try:
        _MutationProbe(store, before).begin(record.module_id)
    except _WriteProposal as proposal:
        after = _snapshot(store, record.snapshot_after_sha256)
        generated = proposal.snapshot
        expected = generated.attempts[-1].model_copy(update={"ticket_id": record.ticket_id})
        generated = generated.model_copy(update={"attempts": (*generated.attempts[:-1], expected)})
        if (
            generated != after
            or record.ticket_id != after.attempts[-1].ticket_id
            or record.attempt != after.attempts[-1].number
        ):
            raise OwnerError("identity_mismatch")
        return
    except OwnerError:
        raise
    except ValueError as error:
        # The one replay of the recorded begin. The core refuses a begin with a
        # ValueError (execution.py:210-213: "a ValueError like every other refusal");
        # a successful begin the core refuses from `before` was never made and is forged.
        raise OwnerError("identity_mismatch") from error
    raise OwnerError("identity_mismatch")


def _verify_outcome(
    store: Execution,
    intent: SubmissionIntent,
    outcome: SubmissionOutcome,
    chain: tuple[ExecutionSnapshot, ...],
) -> set[tuple[str, str]]:
    bound = intent.binding
    rebound, issues = _prepare_bound_readonly(store, intent)
    if rebound != bound:
        raise OwnerError("identity_mismatch")
    by_hash = {s.content_hash(): index for index, s in enumerate(chain)}
    if (
        intent.snapshot_before_sha256 not in by_hash
        or outcome.snapshot_after_sha256 not in by_hash
        or intent.snapshot_before_sha256 != bound.binding.snapshot_sha256
    ):
        raise OwnerError("identity_mismatch")
    start, stop = by_hash[intent.snapshot_before_sha256], by_hash[outcome.snapshot_after_sha256]
    if stop < start:
        raise OwnerError("identity_mismatch")
    if issues:
        if outcome != SubmissionOutcome(
            intent_sha256=intent.content_hash(),
            disposition="refused",
            issues=issues,
            snapshot_after_sha256=intent.snapshot_before_sha256,
            step_sha256=None,
            step_output_sha256=None,
            candidate_sha256=None,
            result_sha256=None,
        ):
            raise OwnerError("identity_mismatch")
        return set()
    if outcome.disposition == "refused" or stop == start:
        raise OwnerError("identity_mismatch")
    edges = set()
    for before, after in zip(chain[start:stop], chain[start + 1 : stop + 1], strict=True):
        if _propose_submission(store, before, bound) != after:
            raise OwnerError("identity_mismatch")
        edges.add((before.content_hash(), after.content_hash()))
    after = chain[stop]
    attempt = next(a for a in after.attempts if a.ticket_id == bound.binding.ticket_id)
    steps = [
        s for s in _new_steps(chain[start], attempt) if s.content_hash() == outcome.step_sha256
    ]
    if len(steps) != 1:
        raise OwnerError("identity_mismatch")
    step = steps[0]
    expected = SubmissionOutcome(
        intent_sha256=intent.content_hash(),
        disposition="valid" if step.status == "valid" and not attempt.issues else "invalid",
        issues=step.issues or attempt.issues,
        snapshot_after_sha256=after.content_hash(),
        step_sha256=step.content_hash(),
        step_output_sha256=step.output_sha256,
        candidate_sha256=attempt.payload_sha256,
        result_sha256=attempt.result_sha256,
    )
    if outcome != expected:
        raise OwnerError("identity_mismatch")
    return edges


def _prepare_bound_readonly(
    store: Execution, intent: SubmissionIntent
) -> tuple[BoundSubmission, tuple[str, ...]]:
    """Recompute bound evidence while denying even idempotent audit writes."""
    bound = intent.binding
    raw = _raw(store, bound.raw_payload_sha256)
    binding = bound.binding
    if isinstance(binding, FinancialBinding):
        calls = _foundation_calls(store, binding)
        prefix = calls[: len(bound.call_ids)]
        if tuple(c.call_id for c in prefix) != bound.call_ids:
            raise OwnerError("identity_mismatch")
        evidence = prefix[-1].source_evidence if prefix else SourceEvidence()
        if binding.step_id in _SOURCE_PHASES:
            _source_session(store, binding)
        filled, normalized, paths, kinds = _filled(
            _historical(store, binding), binding, _text(store, bound.raw_payload_sha256)
        )
        if _raw(store, bound.stored_payload_sha256) != filled.encode():
            raise OwnerError("identity_mismatch")
        reads_by_hash = {
            r.content_hash(): r for r in _records(store, "foundation-reads", InputRead)
        }
        reads = tuple(_known(reads_by_hash, digest) for digest in bound.input_read_hashes)
        for read in reads:
            if read.binding != binding or (read.inputs_sha256, read.body) != _projection(
                store, binding
            ):
                raise OwnerError("identity_mismatch")
        issues = _source_issues(_historical(store, binding), binding, filled, evidence, prefix)
        if binding.step_id not in _SOURCE_PHASES and not reads:
            issues = (*issues, "participation_incomplete")
        try:
            canonical = _SCHEMAS[binding.step_id].model_validate_json(filled).content_hash()
        except ValidationError:
            canonical = None
        rebuilt = BoundSubmission(
            binding=binding,
            raw_payload_sha256=bound.raw_payload_sha256,
            stored_payload_sha256=_hash(filled.encode()),
            canonical_review_sha256=canonical,
            call_ids=tuple(c.call_id for c in prefix),
            successful_call_ids=tuple(c.call_id for c in prefix if c.status == "ok"),
            source_evidence=evidence,
            input_read_hashes=bound.input_read_hashes,
            participation_sha256=None,
            owner_session_id=None,
            normalization_paths=normalized,
            prefilled_paths=paths,
            prefilled_kinds=kinds,
        )
        return rebuilt, issues
    owner_calls = tuple(
        sorted(
            (
                c
                for c in _records(store, "owner-calls", OwnerToolCall)
                if c.receipt.binding.ticket_id == binding.ticket_id
            ),
            key=lambda c: c.ordinal,
        )
    )[: len(bound.call_ids)]
    if tuple(c.receipt.call_id for c in owner_calls) != bound.call_ids:
        raise OwnerError("identity_mismatch")
    session = _intent_session(store, intent)
    owner_session_order = {
        s.session_id: s.index
        for s in _records(store, "owner-sessions", OwnerSession)
        if s.binding.ticket_id == binding.ticket_id
    }
    all_owner_reads = tuple(
        sorted(
            (
                r
                for r in _records(store, "owner-reads", OwnerAccessRead)
                if r.binding.ticket_id == binding.ticket_id
            ),
            key=lambda r: (_known(owner_session_order, r.session_id), r.sequence),
        )
    )
    if (
        tuple(r.content_hash() for r in all_owner_reads[: len(bound.input_read_hashes)])
        != bound.input_read_hashes
    ):
        raise OwnerError("identity_mismatch")
    try:
        review = EarningsDeltaReview.model_validate_json(raw)
    except ValidationError:
        review = None
    participation = None
    issues = () if review is not None else ("bad_arguments",)
    if review is not None:
        _, prior, current = _case_parameters(_historical(store, binding).read().run)
        try:
            if session is None:
                raise OwnerError("participation_incomplete")
            owner_reads_by_hash = {
                r.content_hash(): r for r in _records(store, "owner-reads", OwnerAccessRead)
            }
            owner_reads = tuple(owner_reads_by_hash[digest] for digest in bound.input_read_hashes)
            participation = _participation(
                store, binding, session, owner_reads, owner_calls, prior, current
            )
        except OwnerError as error:
            if error.code not in {"participation_incomplete", "identity_mismatch", "stale_binding"}:
                raise
            issues = (error.code,)
    stored = raw
    if participation is not None and review is not None:
        stored = (
            OwnerSubmissionEnvelope(
                binding=binding,
                raw_review_sha256=bound.raw_payload_sha256,
                review=review,
                participation=participation,
            )
            .model_dump_json()
            .encode()
        )
    if _raw(store, bound.stored_payload_sha256) != stored:
        raise OwnerError("identity_mismatch")
    rebuilt = BoundSubmission(
        binding=binding,
        raw_payload_sha256=bound.raw_payload_sha256,
        stored_payload_sha256=_hash(stored),
        canonical_review_sha256=review.content_hash() if review is not None else None,
        call_ids=tuple(c.receipt.call_id for c in owner_calls),
        successful_call_ids=tuple(
            c.receipt.call_id for c in owner_calls if c.receipt.status == "ok"
        ),
        source_evidence=SourceEvidence(),
        input_read_hashes=bound.input_read_hashes,
        participation_sha256=participation.content_hash() if participation else None,
        owner_session_id=bound.owner_session_id,
        normalization_paths=(),
        prefilled_paths=(),
        prefilled_kinds=(),
    )
    return rebuilt, issues


def _verify_cp5_descendants(store: Execution, anchor: ExecutionSnapshot) -> None:
    from deploy_vii.cp5_integrity import submit_cp5_step

    chain = _chain(store, store.read().content_hash())
    positions = [i for i, s in enumerate(chain) if s == anchor]
    if len(positions) != 1:
        raise OwnerError("identity_mismatch")
    for before, after in zip(chain[positions[0] : -1], chain[positions[0] + 1 :], strict=True):
        if (
            tuple(a for a in after.attempts if a.module_id != "CP-5") != anchor.attempts
            or tuple(h for h in after.heads if h.module_id != "CP-5") != anchor.heads
            or after.run != anchor.run
            or after.pack_sha256 != anchor.pack_sha256
        ):
            raise OwnerError("identity_mismatch")
        probe = _MutationProbe(store, before)
        try:
            if len(after.attempts) == len(before.attempts) + 1:
                if after.attempts[-1].module_id != "CP-5":
                    raise OwnerError("identity_mismatch")
                probe.begin("CP-5")
            else:
                changed = [
                    a for a, b in zip(after.attempts, before.attempts, strict=True) if a != b
                ]
                if len(changed) != 1 or changed[0].module_id != "CP-5" or not changed[0].steps:
                    raise OwnerError("identity_mismatch")
                attempt = changed[0]
                submit_cp5_step(
                    probe,
                    attempt.ticket_id,
                    "integrity_review",
                    probe.payload(attempt.steps[0].payload_sha256),
                )
        except _WriteProposal as proposal:
            expected = proposal.snapshot
            if len(after.attempts) == len(before.attempts) + 1:
                replacement = expected.attempts[-1].model_copy(
                    update={"ticket_id": after.attempts[-1].ticket_id}
                )
                expected = expected.model_copy(
                    update={"attempts": (*expected.attempts[:-1], replacement)}
                )
            if expected != after:
                raise OwnerError("identity_mismatch")
        else:
            raise OwnerError("identity_mismatch")


def _policy(case_manifest: Path) -> str:
    if _hash((case_manifest.parent / "transport-expected.json").read_bytes()) != _POLICY_SHA256:
        raise OwnerError("identity_mismatch")
    return _POLICY_SHA256


def _setup(store: Execution, case_manifest: Path) -> tuple[OwnerSetup, dict[str, Any]]:
    records = _records(store, "setup", OwnerSetup)
    if len(records) != 1:
        raise OwnerError("identity_mismatch")
    setup = records[0]
    current = store.read()
    chain = _chain(store, current.content_hash())
    first = chain[0]
    if (
        first.content_hash() != setup.initial_snapshot_sha256
        or first.parent is not None
        or first.attempts
        or first.heads
        or first.run != setup.run
        or first.pack_sha256 != setup.pack_sha256
        or first != ExecutionSnapshot(run=setup.run, pack_sha256=setup.pack_sha256)
        or setup.policy_sha256 != _policy(case_manifest)
    ):
        raise OwnerError("identity_mismatch")
    case, pins = _case_pins(case_manifest, setup.case_id, store.pack(first))
    if pins != setup.pins:
        raise OwnerError("identity_mismatch")
    return setup, case


def _transcript_fields(store: Execution) -> dict[str, Any]:
    positions = {
        s.content_hash(): index
        for index, s in enumerate(_chain(store, _head(store).content_hash()))
    }
    sessions = tuple(
        sorted(
            _records(store, "owner-sessions", OwnerSession),
            key=lambda s: (_known(positions, s.binding.snapshot_sha256), s.index),
        )
    )
    session_order = {s.session_id: index for index, s in enumerate(sessions)}
    intents = tuple(sorted(_records(store, "intents", SubmissionIntent), key=lambda i: i.index))
    intent_order = {i.content_hash(): i.index for i in intents}
    return {
        "transport_messages": tuple(
            sorted(_records(store, "transport-messages", TransportMessage), key=lambda m: m.index)
        ),
        "begins": tuple(sorted(_records(store, "begins", BeginRecord), key=lambda b: b.index)),
        "foundation_calls": tuple(
            sorted(
                _records(store, "foundation-calls", FinancialCall),
                key=lambda c: (_known(positions, c.binding.snapshot_sha256), c.sequence),
            )
        ),
        "foundation_input_reads": tuple(
            sorted(
                _records(store, "foundation-reads", InputRead),
                key=lambda r: (_known(positions, r.binding.snapshot_sha256), r.sequence),
            )
        ),
        "owner_sessions": sessions,
        "owner_access_reads": tuple(
            sorted(
                _records(store, "owner-reads", OwnerAccessRead),
                key=lambda r: (_known(session_order, r.session_id), r.sequence),
            )
        ),
        "owner_calls": tuple(
            sorted(_records(store, "owner-calls", OwnerToolCall), key=lambda c: c.ordinal)
        ),
        "submission_intents": intents,
        "submission_outcomes": tuple(
            sorted(
                _records(store, "outcomes", SubmissionOutcome),
                key=lambda o: _known(intent_order, o.intent_sha256),
            )
        ),
    }


def _verify_begins(store: Execution, begins: tuple[BeginRecord, ...]) -> set[tuple[str, str]]:
    """Authenticate every begin record; return the chain edges the successful ones cover.

    Indices are contiguous from 1; each successful begin covers a distinct edge; a
    refusal ends the run (complete or failed, no further begin), so at most one begin
    is a refusal and it is the last.
    """
    if [b.index for b in begins] != list(range(1, len(begins) + 1)):
        raise OwnerError("identity_mismatch")
    refusals = [b.index for b in begins if b.error_code is not None]
    if len(refusals) > 1 or (refusals and refusals[0] != len(begins)):
        raise OwnerError("identity_mismatch")
    covered: set[tuple[str, str]] = set()
    for begin in begins:
        _verify_begin(store, begin)
        if begin.error_code is None:
            edge = (begin.snapshot_before_sha256, begin.snapshot_after_sha256)
            if edge in covered:
                raise OwnerError("identity_mismatch")
            covered.add(edge)
    return covered


def _verify_open_history(
    store: Execution, setup: OwnerSetup, recovered: BeginRecord | None = None
) -> None:
    """Authenticate the stored history, plus the begin record `_bootstrap_log` recovered.

    `recovered` is held in memory only: it is authenticated here together with the
    stored begins (`_verify_begins`) and every later check, and the caller retains it
    only after this returns. The caller has re-read the head under the lock first, so
    a concurrent opener's crashed core begin cannot leave the binding stale after the
    retain: an open that refuses writes nothing, except the recorded CP-1B `_activate`
    derivation residual (QUEUE, review-adversary-fix-5 L-2).
    """
    fields = _transcript_fields(store)
    chain = _chain(store, _head(store).content_hash())
    begins = fields["begins"] if recovered is None else (*fields["begins"], recovered)
    covered = _verify_begins(store, begins)
    outcomes = {o.intent_sha256: o for o in fields["submission_outcomes"]}
    pending = _unresolved(store)
    for intent in fields["submission_intents"]:
        stored_binding = _stored_bytes(store, "bindings", intent.binding.content_hash())
        if stored_binding != intent.binding.model_dump_json().encode():
            raise OwnerError("identity_mismatch")
        if intent.content_hash() in outcomes:
            edges = _verify_outcome(store, intent, outcomes[intent.content_hash()], chain)
        else:
            if not pending or intent != pending[0]:
                raise OwnerError("identity_mismatch")
            rebound, issues = _prepare_bound_readonly(store, intent)
            if (
                rebound != intent.binding
                or intent.snapshot_before_sha256 != intent.binding.binding.snapshot_sha256
            ):
                raise OwnerError("identity_mismatch")
            start = next(
                (
                    index
                    for index, s in enumerate(chain)
                    if s.content_hash() == intent.snapshot_before_sha256
                ),
                None,
            )
            if start is None:
                raise OwnerError("identity_mismatch")
            edges = set()
            if issues and start != len(chain) - 1:
                raise OwnerError("identity_mismatch")
            for before, after in zip(chain[start:-1], chain[start + 1 :], strict=True):
                if _propose_submission(store, before, intent.binding) != after:
                    raise OwnerError("identity_mismatch")
                edges.add((before.content_hash(), after.content_hash()))
        if covered & edges:
            raise OwnerError("identity_mismatch")
        covered.update(edges)
    if covered != {(a.content_hash(), b.content_hash()) for a, b in itertools.pairwise(chain)}:
        raise OwnerError("identity_mismatch")
    # A private in-memory view supplies only already authenticated immutable
    # records to the common checks; it is never persisted as setup authority.
    _verify_transcripts(
        store,
        _TranscriptRecords(
            run=setup.run,
            foundation_calls=fields["foundation_calls"],
            foundation_input_reads=fields["foundation_input_reads"],
            owner_sessions=fields["owner_sessions"],
            owner_access_reads=fields["owner_access_reads"],
            owner_calls=fields["owner_calls"],
        ),
    )


def _bootstrap_log(store: Execution, setup: OwnerSetup) -> BeginRecord | None:
    """Compute the one begin record a crash between a core begin and its retention loses.

    `_begin` writes the core snapshot first and the BeginRecord second, so a crash in
    between leaves exactly this state: the last chain edge has no record and no stored
    record is bound to the head, because every record bound to a head (foundation
    calls and reads, owner sessions, reads and calls, bindings, intents, outcomes,
    participations) is written only after the begin record. Begin 1 is recovered
    against the setup record; a later begin by `_recover_last_begin`. A last record
    deleted inside that window is indistinguishable from the crash and is recovered to
    the same replay-verified state; one deleted after a record bound to its head was
    written is not, and is left, like every other gap, to `_verify_open_history` to
    refuse. Nothing is written here: the caller authenticates the returned record with
    the stored history (`_verify_open_history`) and retains it only after that passes.
    """
    begins = tuple(sorted(_records(store, "begins", BeginRecord), key=lambda b: b.index))
    chain = _chain(store, _head(store).content_hash())
    if len(chain) == 1:
        return None
    if begins:
        return _recover_last_begin(store, begins, chain)
    first, current = chain[0], chain[-1]
    if (
        len(chain) != 2
        or first.content_hash() != setup.initial_snapshot_sha256
        or current.heads
        or len(current.attempts) != 1
        or any(e.kind != "setup" for e in _inventory(store))
    ):
        raise OwnerError("identity_mismatch")
    attempt = current.attempts[0]
    expected = Attempt(
        ticket_id=attempt.ticket_id,
        module_id="CP-0",
        inputs=current_inputs(first, "CP-0"),
        number=0,
    )
    if attempt != expected:
        raise OwnerError("identity_mismatch")
    return BeginRecord(
        index=1,
        module_id="CP-0",
        snapshot_before_sha256=first.content_hash(),
        snapshot_after_sha256=current.content_hash(),
        ticket_id=attempt.ticket_id,
        attempt=0,
        error_code=None,
    )


def _bound_to(store: Execution, digest: str) -> bool:
    """Whether any stored record is bound to the snapshot `digest`.

    Every record a run writes after a begin names the begin's head: foundation calls and
    reads, owner sessions, reads and calls, bindings and participations through their
    binding, intents through `snapshot_before_sha256`, outcomes through
    `snapshot_after_sha256`. All are written only after the BeginRecord is retained.
    """
    return (
        any(
            c.binding.snapshot_sha256 == digest
            for c in _records(store, "foundation-calls", FinancialCall)
        )
        or any(
            r.binding.snapshot_sha256 == digest
            for r in _records(store, "foundation-reads", InputRead)
        )
        or any(
            s.binding.snapshot_sha256 == digest
            for s in _records(store, "owner-sessions", OwnerSession)
        )
        or any(
            r.binding.snapshot_sha256 == digest
            for r in _records(store, "owner-reads", OwnerAccessRead)
        )
        or any(
            c.receipt.binding.snapshot_sha256 == digest
            for c in _records(store, "owner-calls", OwnerToolCall)
        )
        or any(
            b.binding.snapshot_sha256 == digest
            for b in _records(store, "bindings", BoundSubmission)
        )
        or any(
            i.snapshot_before_sha256 == digest or i.binding.binding.snapshot_sha256 == digest
            for i in _records(store, "intents", SubmissionIntent)
        )
        or any(
            o.snapshot_after_sha256 == digest
            for o in _records(store, "outcomes", SubmissionOutcome)
        )
        or any(
            p.binding.snapshot_sha256 == digest
            for p in _records(store, "participations", EarningsParticipation)
        )
    )


def _recover_last_begin(
    store: Execution, begins: tuple[BeginRecord, ...], chain: tuple[ExecutionSnapshot, ...]
) -> BeginRecord | None:
    """Synthesise the begin record of the last chain edge when only that record is lost.

    Only the last edge is recoverable, and only inside the crash window: no stored
    record is bound to the head, its `before` has no pending attempt and the head adds
    exactly one pending attempt with a fresh ticket, which is what a core `begin()`
    writes (execution.py:626-641) and nothing else does. The record is returned, not
    retained: `_verify_open_history` authenticates it with the stored begins (the same
    core replay, `_verify_begin`) and the rest of the history before the caller retains it.
    """
    before, head = chain[-2], chain[-1]
    if (
        [b.index for b in begins] != list(range(1, len(begins) + 1))
        or any(b.error_code is not None for b in begins)
        or any(b.snapshot_after_sha256 == head.content_hash() for b in begins)
        or any(a.status == "pending" for a in before.attempts)
        or _bound_to(store, head.content_hash())
    ):
        # Not the crash state: a refusal ends the run, a begin reaching the head needs
        # no recovery, a pending attempt in `before` makes the last edge a submission
        # edge, and a record bound to the head was written after the begin record, so
        # that record was deleted. The records are judged as stored by
        # `_verify_open_history`.
        return None
    added = head.attempts[len(before.attempts) :]
    if (
        len(added) != 1
        or added[0].status != "pending"
        or added[0].module_id not in {"CP-0", "CP-1", "CP-1B"}
        or any(a.ticket_id == added[0].ticket_id for a in before.attempts)
        or head
        != before.model_copy(
            update={"parent": before.content_hash(), "attempts": (*before.attempts, added[0])}
        )
    ):
        # The last edge is uncovered and `before` is idle, so only a core begin can have
        # produced the head; any other head is an altered journal. A core begin's ticket
        # is fresh (`_historical` requires one match), which the replay in
        # `_verify_begin` cannot see because it adopts the recorded ticket.
        raise OwnerError("identity_mismatch")
    return BeginRecord(
        index=len(begins) + 1,
        module_id=cast(Literal["CP-0", "CP-1", "CP-1B"], added[0].module_id),
        snapshot_before_sha256=before.content_hash(),
        snapshot_after_sha256=head.content_hash(),
        ticket_id=added[0].ticket_id,
        attempt=added[0].number,
        error_code=None,
    )


@dataclass(frozen=True, slots=True)
class _TranscriptRecords:
    run: Run
    foundation_calls: tuple[FinancialCall, ...]
    foundation_input_reads: tuple[InputRead, ...]
    owner_sessions: tuple[OwnerSession, ...]
    owner_access_reads: tuple[OwnerAccessRead, ...]
    owner_calls: tuple[OwnerToolCall, ...]


def _verify_transcripts(
    store: Execution, receipt: EarningsOwnerReceipt | _TranscriptRecords
) -> None:
    calls_by_binding: dict[str, list[FinancialCall]] = {}
    budgets: dict[tuple[str, str], int] = {}
    call_ids = []
    for call in receipt.foundation_calls:
        binding = call.binding
        if binding.step_id not in _SOURCE_PHASES:
            raise OwnerError("identity_mismatch")
        key = (binding.ticket_id, binding.step_id)
        budgets[key] = budgets.get(key, 0) + 1
        if budgets[key] > MAX_FOUNDATION:
            raise OwnerError("transport_limit")
        calls_by_binding.setdefault(binding.content_hash(), []).append(call)
        call_ids.append(call.call_id)
    for calls in calls_by_binding.values():
        ordered = tuple(sorted(calls, key=lambda c: c.sequence))
        if ordered != _foundation_calls(store, ordered[0].binding):
            raise OwnerError("identity_mismatch")
        _source_session(store, ordered[0].binding)
    reads_by_binding: dict[str, list[InputRead]] = {}
    read_budgets: dict[tuple[str, str], int] = {}
    for read in receipt.foundation_input_reads:
        key = (read.binding.ticket_id, read.binding.step_id)
        read_budgets[key] = read_budgets.get(key, 0) + 1
        if read_budgets[key] > MAX_FOUNDATION or (read.inputs_sha256, read.body) != _projection(
            store, read.binding
        ):
            raise OwnerError("identity_mismatch")
        reads_by_binding.setdefault(read.binding.content_hash(), []).append(read)
    for reads in reads_by_binding.values():
        if sorted(r.sequence for r in reads) != list(range(1, len(reads) + 1)):
            raise OwnerError("identity_mismatch")
    sessions = {s.session_id: s for s in receipt.owner_sessions}
    if len(sessions) != len(receipt.owner_sessions):
        raise OwnerError("identity_mismatch")
    for ticket_id in {s.binding.ticket_id for s in receipt.owner_sessions}:
        indexed = sorted(
            s.index for s in receipt.owner_sessions if s.binding.ticket_id == ticket_id
        )
        if indexed != list(range(1, len(indexed) + 1)) or len(indexed) > MAX_OWNER_SESSIONS:
            raise OwnerError("identity_mismatch")
    if tuple(c.ordinal for c in receipt.owner_calls) != tuple(
        range(1, len(receipt.owner_calls) + 1)
    ):
        raise OwnerError("identity_mismatch")
    for session in receipt.owner_sessions:
        _, prior, current = _case_parameters(receipt.run)
        owner_calls = tuple(c for c in receipt.owner_calls if c.session_id == session.session_id)
        _owner_session_proof(store, session, owner_calls, prior, current)
        owner_reads = tuple(
            r for r in receipt.owner_access_reads if r.session_id == session.session_id
        )
        if (
            [r.sequence for r in owner_reads] != list(range(1, len(owner_reads) + 1))
            or len(owner_reads) > MAX_ACCESS_READS
            or any(
                r.binding != session.binding
                or r.access_manifest_json != session.access_manifest_json
                for r in owner_reads
            )
        ):
            raise OwnerError("identity_mismatch")
    if any(c.session_id not in sessions for c in receipt.owner_calls) or any(
        r.session_id not in sessions for r in receipt.owner_access_reads
    ):
        raise OwnerError("identity_mismatch")
    for ticket_id in {c.receipt.binding.ticket_id for c in receipt.owner_calls}:
        if (
            sum(c.receipt.binding.ticket_id == ticket_id for c in receipt.owner_calls)
            > MAX_OWNER_CALLS
        ):
            raise OwnerError("transport_limit")
    call_ids.extend(c.receipt.call_id for c in receipt.owner_calls)
    if len(call_ids) != len(set(call_ids)):
        raise OwnerError("identity_mismatch")


def _expected_inventory(store: Execution, receipt: EarningsOwnerReceipt) -> tuple[AuditEntry, ...]:
    entries: set[tuple[str, str]] = set()
    setup, _ = _setup(store, _CASE_MANIFEST)
    entries.add(("setup", setup.content_hash()))
    embedded = {
        "transport-messages": receipt.transport_messages,
        "begins": receipt.begins,
        "foundation-calls": receipt.foundation_calls,
        "foundation-reads": receipt.foundation_input_reads,
        "owner-sessions": receipt.owner_sessions,
        "owner-reads": receipt.owner_access_reads,
        "owner-calls": receipt.owner_calls,
        "intents": receipt.submission_intents,
        "outcomes": receipt.submission_outcomes,
    }
    for kind, records in embedded.items():
        for record in records:
            entries.add((kind, record.content_hash()))
            if (
                _stored_bytes(store, kind, record.content_hash())
                != record.model_dump_json().encode()
            ):
                raise OwnerError("identity_mismatch")
    for intent in receipt.submission_intents:
        bound = intent.binding
        entries.add(("bindings", bound.content_hash()))
        if (
            _stored_bytes(store, "bindings", bound.content_hash())
            != bound.model_dump_json().encode()
        ):
            raise OwnerError("identity_mismatch")
        entries.update(
            ("payloads", digest)
            for digest in (bound.raw_payload_sha256, bound.stored_payload_sha256)
        )
        if bound.participation_sha256 is not None:
            entries.add(("participations", bound.participation_sha256))
            envelope = OwnerSubmissionEnvelope.model_validate_json(
                _raw(store, bound.stored_payload_sha256)
            )
            if (
                envelope.participation.content_hash() != bound.participation_sha256
                or _stored_bytes(store, "participations", bound.participation_sha256)
                != envelope.participation.model_dump_json().encode()
            ):
                raise OwnerError("identity_mismatch")
    intents = {i.content_hash(): i for i in receipt.submission_intents}
    for outcome in receipt.submission_outcomes:
        if outcome.intent_sha256 not in intents:
            raise OwnerError("identity_mismatch")
        if outcome.candidate_sha256 is not None:
            entries.add(("payloads", outcome.candidate_sha256))
            with _stored_read():
                journal_candidate = store.payload(outcome.candidate_sha256)
            if _text(store, outcome.candidate_sha256) != journal_candidate:
                raise OwnerError("identity_mismatch")
        if (
            isinstance(intents[outcome.intent_sha256].binding.binding, OwnerBinding)
            and outcome.step_output_sha256 is not None
        ):
            entries.add(("stages", outcome.step_output_sha256))
            with _stored_read():
                stored_stage = store.step_output(outcome.step_output_sha256)
            # The blob is authenticated by the core read above and matched to the step
            # by `_verify_outcome`; a stage that no longer parses is a B1 schema or
            # composition defect, which propagates (lease: programming failures propagate).
            stage = EarningsOwnerStage.model_validate_json(stored_stage)
            envelope = OwnerSubmissionEnvelope.model_validate_json(
                _raw(store, intents[outcome.intent_sha256].binding.stored_payload_sha256)
            )
            if (
                _owner_stage(store, envelope) != stage
                or _stored_bytes(store, "stages", outcome.step_output_sha256)
                != stage.model_dump_json().encode()
            ):
                raise OwnerError("identity_mismatch")
    for message in receipt.transport_messages:
        entries.add(("payloads", message.request_sha256))
    return tuple(
        _parse(AuditEntry, {"kind": kind, "sha256": digest}) for kind, digest in sorted(entries)
    )


def _verify_owner(store: Execution, receipt: EarningsOwnerReceipt, *, sealed: bool) -> None:
    receipt = EarningsOwnerReceipt.model_validate_json(receipt.model_dump_json())
    anchor = _snapshot(store, receipt.owner_snapshot_sha256)
    case, pins = _case_pins(_CASE_MANIFEST, receipt.case_id, store.pack(anchor))
    setup, _ = _setup(store, _CASE_MANIFEST)
    if (
        setup.run,
        setup.pack_sha256,
        setup.case_id,
        setup.pins,
        setup.participant,
        setup.transport,
    ) != (
        receipt.run,
        receipt.pack_sha256,
        receipt.case_id,
        receipt.pins,
        receipt.participant,
        receipt.transport,
    ):
        raise OwnerError("identity_mismatch")
    if (
        receipt.run != anchor.run
        or receipt.pack_sha256 != anchor.pack_sha256
        or receipt.pins != pins
        or _unresolved(store)
        or len(receipt.model_dump_json().encode()) > MAX_RECEIPT
    ):
        raise OwnerError("identity_mismatch")
    chain = _chain(store, receipt.owner_snapshot_sha256)
    if chain[0].attempts or chain[0].heads:
        raise OwnerError("identity_mismatch")
    covered = _verify_begins(store, receipt.begins)
    outcomes = {o.intent_sha256: o for o in receipt.submission_outcomes}
    if (
        len(outcomes) != len(receipt.submission_outcomes)
        or len(outcomes) != len(receipt.submission_intents)
        or [i.index for i in receipt.submission_intents]
        != list(range(1, len(receipt.submission_intents) + 1))
    ):
        raise OwnerError("identity_mismatch")
    budgets: dict[tuple[str, str], int] = {}
    for intent in receipt.submission_intents:
        key = (intent.binding.binding.ticket_id, intent.binding.binding.step_id)
        budgets[key] = budgets.get(key, 0) + 1
        if budgets[key] > MAX_FOUNDATION or intent.content_hash() not in outcomes:
            raise OwnerError("identity_mismatch")
        edges = _verify_outcome(store, intent, outcomes[intent.content_hash()], chain)
        if covered & edges:
            raise OwnerError("identity_mismatch")
        covered.update(edges)
    if covered != {(a.content_hash(), b.content_hash()) for a, b in itertools.pairwise(chain)}:
        raise OwnerError("identity_mismatch")
    _verify_transcripts(store, receipt)
    if _head_record(store, anchor, "CP-0") != receipt.cp0:
        raise OwnerError("identity_mismatch")
    if receipt.outcome == "owner_settled":
        if (
            tuple(h.module_id for h in anchor.heads) != ("CP-0", "CP-1", "CP-1B")
            or any(a.status == "pending" for a in anchor.attempts)
            or _head_record(store, anchor, "CP-1") != receipt.cp1
            or _head_record(store, anchor, "CP-1B") != receipt.cp1b
            or receipt.cp1b is None
            or receipt.cp1b.head.status != "restricted"
            or receipt.cp1b.head.qualification is not None
            or receipt.cp1 is None
            or receipt.cp1.head.qualification != PROMOTED
        ):
            raise OwnerError("identity_mismatch")
        attempt = next(a for a in anchor.attempts if a.ticket_id == receipt.cp1b.ticket_id)
        if len(attempt.steps) != 1 or attempt.steps[0].output_sha256 != receipt.cp1b_stage_sha256:
            raise OwnerError("identity_mismatch")
        _verify_cp5_descendants(store, anchor)
    elif (
        tuple(h.module_id for h in anchor.heads) != ("CP-0",)
        or receipt.cp0.head.status != "restricted"
        or store.read() != anchor
        or any(a.module_id != "CP-0" for a in anchor.attempts)
        or not any(
            b.module_id == "CP-1" and b.error_code == "not_authorized" for b in receipt.begins
        )
        or case["source_state"] != "financial_missing"
    ):
        raise OwnerError("identity_mismatch")
    expected = _expected_inventory(store, receipt)
    if receipt.audit_inventory != expected or _inventory(store) != expected:
        raise OwnerError("identity_mismatch")
    if receipt.transport == "python-api" and receipt.transport_messages:
        raise OwnerError("identity_mismatch")
    if [m.index for m in receipt.transport_messages] != list(
        range(1, len(receipt.transport_messages) + 1)
    ) or len(receipt.transport_messages) > MAX_MESSAGES:
        raise OwnerError("identity_mismatch")
    for message in receipt.transport_messages:
        operation, _, _ = _classify_frame(_raw(store, message.request_sha256))
        if message.operation != operation:
            raise OwnerError("identity_mismatch")
    if sealed:
        root = store.directory / "earnings-owner-audit"
        if (root / "owner-receipt.json").read_bytes() != receipt.model_dump_json().encode() or (
            root / "owner-receipt.sha256"
        ).read_bytes() != receipt.content_hash().encode("ascii"):
            raise OwnerError("identity_mismatch")


_KNOWN_CORE_TAMPER = {
    "Execution snapshot hash mismatch",
    "Execution result blob is not the canonical module",
    "Execution head does not match its result blob",
    "Execution head commands do not match its result blob",
    "Execution head status does not match its result blob",
    "Execution pack blob is not the canonical pack of this snapshot",
    "Required upstream is unrun, stale or blocked",
    "Module is not selected for this run",
    "Invalid blob hash",
    "Invalid execution pointer",
}


@contextmanager
def _tamper_is_identity_mismatch() -> Iterator[None]:
    """Map the known ways tampered or missing stored evidence fails to `identity_mismatch`.

    Fail-closed, never a success path: each listed error means stored evidence is
    absent, malformed or inconsistent, so the caller is refused. `KeyError` and
    `StopIteration` come from looking up records the verified prefix requires
    (`next(...)` and dict indexing over audit data), so a missing record is tamper.
    The mapping can also hide a programming defect of the same type, so the original
    error is kept as `__cause__` (never sent to the actor, whose reply carries only
    the category). Any other `ValueError`, including unknown core messages, propagates.
    """
    try:
        yield
    except OwnerError:
        raise
    except (
        ValidationError,
        FileNotFoundError,
        IsADirectoryError,
        KeyError,
        StopIteration,
        UnicodeDecodeError,
    ) as error:
        raise OwnerError("identity_mismatch") from error
    except ValueError as error:
        if str(error) in _KNOWN_CORE_TAMPER or re.fullmatch(
            r"Execution blob [0-9a-f]{64} (?:is missing|hash mismatch)", str(error)
        ):
            raise OwnerError("identity_mismatch") from error
        raise


def _earlier_receipt(raw: bytes, receipt: EarningsOwnerReceipt) -> bool:
    """`raw` is this store's receipt from an earlier attempt that crashed before the seal."""
    with _stored_read():
        earlier = EarningsOwnerReceipt.model_validate_json(raw)
    later = receipt.transport_messages
    return (
        earlier.model_dump_json().encode() == raw
        and later[: len(earlier.transport_messages)] == earlier.transport_messages
        and all(entry in receipt.audit_inventory for entry in earlier.audit_inventory)
        and earlier.model_copy(
            update={"transport_messages": later, "audit_inventory": receipt.audit_inventory}
        )
        == receipt
    )


def verify_earnings_owner_receipt(store: Execution, receipt: EarningsOwnerReceipt) -> None:
    """Read-only authentication of the owner prefix and permitted CP5 descendants."""
    with _tamper_is_identity_mismatch():
        _verify_owner(store, receipt, sealed=True)


class EarningsWorkflow:
    """One writer over a fresh source foundation and immutable owner evidence."""

    def __init__(self) -> None:
        raise OwnerError("not_permitted")

    @classmethod
    def create(
        cls,
        directory: Path,
        pack: PreparedPack,
        *,
        case_manifest: Path,
        case_id: OwnerCaseId,
        participant: str = "trusted-python",
        transport: Transport = "python-api",
    ) -> EarningsWorkflow:
        if (
            type(participant) is not str
            or not participant
            or transport not in {"python-api", "bounded-json-lines/1"}
        ):
            raise OwnerError("bad_arguments")
        pack = PreparedPack.model_validate_json(pack.model_dump_json())
        case, pins = _case_pins(case_manifest, case_id, pack)
        policy = _policy(case_manifest)
        store = Execution.create(directory, pack)
        initial = store.read()
        if initial != ExecutionSnapshot(run=pack.run, pack_sha256=pack.content_hash()):
            raise OwnerError("identity_mismatch")
        setup = OwnerSetup(
            run=pack.run,
            pack_sha256=pack.content_hash(),
            initial_snapshot_sha256=initial.content_hash(),
            case_id=case_id,
            pins=pins,
            participant=participant,
            transport=transport,
            policy_sha256=policy,
        )
        _retain(store, "setup", setup)
        instance = object.__new__(cls)
        instance._initialize(store, case)
        instance._setup_record = setup
        with instance._locked():
            attempt = instance._begin("CP-0")
            if attempt is None:
                raise OwnerError("identity_mismatch")
            instance._activate(attempt, "source_readiness")
        return instance

    @classmethod
    def open(
        cls, directory: Path, *, case_manifest: Path, participant: str, transport: Transport
    ) -> EarningsWorkflow:
        store = Execution(directory)
        try:
            setup, case = _setup(store, case_manifest)
            if participant != setup.participant or transport != setup.transport:
                raise OwnerError("identity_mismatch")
        except (ValidationError, FileNotFoundError, KeyError, StopIteration, ValueError) as error:
            # Fail-closed: the setup record or case manifest is absent or malformed,
            # so the store cannot be opened. ValueError is deliberately broad here
            # because every setup failure means the store is not a valid B1 store;
            # the original error is kept as __cause__ for the operator.
            if isinstance(error, OwnerError):
                raise
            raise OwnerError("identity_mismatch") from error
        instance = object.__new__(cls)
        instance._initialize(store, case)
        instance._setup_record = setup
        with instance._locked(inspect_sealed=True):
            if instance._sealed:
                with _stored_read():
                    receipt = EarningsOwnerReceipt.model_validate_json(
                        (directory / "earnings-owner-audit/owner-receipt.json").read_bytes()
                    )
                verify_earnings_owner_receipt(store, receipt)
                instance._phase, instance._outcome = "complete", receipt.outcome
                return instance
            # `_initialize` read the head before the lock; another opener may have moved
            # it since (a core begin whose BeginRecord then crashed). Read it again under
            # the lock, or `_activate` below would refuse `stale_binding` after the retain.
            instance._current_sha256 = _head(store).content_hash()
            recovered = _bootstrap_log(store, setup)
            _verify_open_history(store, setup, recovered)
            if recovered is not None:
                # Retained only now, after the whole stored history authenticated it, so
                # an open that refuses leaves the store byte-identical, except the recorded
                # CP-1B `_activate` derivation residual (QUEUE, review-adversary-fix-5 L-2);
                # and before the resume below, which writes records bound to the head.
                _retain(store, "begins", recovered)
            snapshot = _head(store)
            if snapshot.content_hash() == setup.initial_snapshot_sha256:
                attempt = instance._begin("CP-0")
                if attempt is None:
                    raise OwnerError("identity_mismatch")
                instance._activate(attempt, "source_readiness")
                return instance
            unresolved = _unresolved(store)
            if unresolved:
                instance._binding = unresolved[0].binding.binding
                instance._phase = cast(Phase, instance._binding.step_id)
                instance._owner_session = _intent_session(store, unresolved[0])
                return instance
            pending = [a for a in snapshot.attempts if a.status == "pending"]
            if len(pending) > 1:
                raise OwnerError("identity_mismatch")
            if pending:
                attempt = pending[0]
                if attempt.module_id == "CP-0":
                    phase = "source_readiness"
                elif attempt.module_id == "CP-1B":
                    phase = "earnings_delta"
                else:
                    phase = CP1_PROMOTION[len(attempt.steps)]
                instance._activate(attempt, phase, replay=True)
                return instance
            begins = _records(store, "begins", BeginRecord)
            if any(b.error_code == "not_authorized" for b in begins):
                if case["source_state"] == "financial_missing":
                    instance._phase, instance._outcome = "complete", "cp1_not_authorized"
                else:
                    instance._phase, instance._outcome = "failed", None
                return instance
            intents = sorted(_records(store, "intents", SubmissionIntent), key=lambda i: i.index)
            outcomes = {o.intent_sha256: o for o in _records(store, "outcomes", SubmissionOutcome)}
            if not intents or intents[-1].content_hash() not in outcomes:
                raise OwnerError("identity_mismatch")
            instance._binding = intents[-1].binding.binding
            instance._advance(outcomes[intents[-1].content_hash()], intents[-1].binding)
        return instance

    def _initialize(self, store: Execution, case: dict[str, Any]) -> None:
        self._store = store
        self._case = case
        self._operation = Lock()
        self._dispatcher = Lock()
        self._current_sha256 = store.read().content_hash()
        self._source: SourceSession | None = None
        self._upstream: UpstreamTools | None = None
        self._owner_session: OwnerSession | None = None
        self._binding: FinancialBinding | OwnerBinding | None = None
        self._phase: Phase = "failed"
        self._outcome: OutcomeKind | None = None
        self._setup_record: OwnerSetup
        self._sealed = _sealed_on_disk(store)

    @contextmanager
    def _locked(self, *, inspect_sealed: bool = False) -> Iterator[None]:
        import fcntl

        if not self._operation.acquire(blocking=False):
            raise OwnerError("not_permitted")
        try:
            with (self._store.directory / ".earnings-owner.lock").open("a") as stream:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise OwnerError("not_permitted") from None
                try:
                    # Another instance may have sealed since `_initialize` read the flag;
                    # the seal is read again under the lock, before anything is written.
                    self._sealed = self._sealed or _sealed_on_disk(self._store)
                    if self._sealed and not inspect_sealed:
                        raise OwnerError("not_permitted")
                    yield
                finally:
                    fcntl.flock(stream, fcntl.LOCK_UN)
        finally:
            self._operation.release()

    def _current(self) -> ExecutionSnapshot:
        snapshot = self._store.read()
        if snapshot.content_hash() != self._current_sha256:
            raise OwnerError("stale_binding")
        with _stored_read():
            self._store.pack(snapshot)
        return snapshot

    def _begin(self, module_id: str) -> Attempt | None:
        if module_id not in {"CP-0", "CP-1", "CP-1B"}:
            raise OwnerError("not_permitted")
        selected = cast(Literal["CP-0", "CP-1", "CP-1B"], module_id)
        before = self._current()
        records = _records(self._store, "begins", BeginRecord)
        try:
            attempt = self._store.begin(module_id)
        except NotAuthorized:
            if module_id != "CP-1" or self._store.read().content_hash() != before.content_hash():
                raise OwnerError("identity_mismatch") from None
            record = BeginRecord(
                index=len(records) + 1,
                module_id=selected,
                snapshot_before_sha256=before.content_hash(),
                snapshot_after_sha256=before.content_hash(),
                ticket_id=None,
                attempt=None,
                error_code="not_authorized",
            )
            _retain(self._store, "begins", record)
            if self._case["source_state"] != "financial_missing":
                # An actual NotAuthorized on a case whose source is present came
                # from the actor's CP0 review, not a source gap: not a genuine
                # negative, so the run fails rather than claiming the negative outcome.
                self._phase, self._outcome, self._binding = "failed", None, None
                return None
            self._phase, self._outcome, self._binding = "complete", "cp1_not_authorized", None
            return None
        after = self._store.read()
        record = BeginRecord(
            index=len(records) + 1,
            module_id=selected,
            snapshot_before_sha256=before.content_hash(),
            snapshot_after_sha256=after.content_hash(),
            ticket_id=attempt.ticket_id,
            attempt=attempt.number,
            error_code=None,
        )
        _retain(self._store, "begins", record)
        self._current_sha256 = after.content_hash()
        return attempt

    def _activate(self, attempt: Attempt, phase: str, *, replay: bool = False) -> None:
        if phase not in _SCHEMAS:
            raise OwnerError("not_permitted")
        snapshot = self._current()
        self._binding = _binding(snapshot, attempt, phase)
        self._phase, self._outcome = cast(Phase, phase), None
        self._source = None
        self._upstream = None
        self._owner_session = None
        if isinstance(self._binding, FinancialBinding) and phase in _SOURCE_PHASES:
            self._source = (
                _source_session(self._store, self._binding)
                if replay
                else SourceSession.from_execution(self._store, attempt.ticket_id, phase)
            )
        elif isinstance(self._binding, OwnerBinding):
            sessions = tuple(
                s
                for s in _records(self._store, "owner-sessions", OwnerSession)
                if s.binding.ticket_id == attempt.ticket_id
            )
            if len(sessions) >= MAX_OWNER_SESSIONS:
                raise OwnerError("transport_limit")
            grant, _, producer = _grant(
                self._store,
                self._binding,
                self._case["prior_period_id"],
                self._case["current_period_id"],
            )
            tools = UpstreamTools.from_execution(
                self._store, attempt.ticket_id, "earnings_delta", grants=grant
            )
            header = tools.access_manifest
            if header != _manifest(self._binding, grant, producer):
                raise OwnerError("identity_mismatch")
            record = OwnerSession(
                session_id="owner-session:" + uuid4().hex,
                index=len(sessions) + 1,
                binding=self._binding,
                normalized_grant_json=_canonical(grant),
                access_manifest_json=_canonical(header),
            )
            self._current()
            _retain(self._store, "owner-sessions", record)
            self._upstream, self._owner_session = tools, record

    def state(self) -> WorkflowState:
        with self._locked(inspect_sealed=True):
            self._current()
            binding = self._binding if self._phase not in {"complete", "failed"} else None
            return WorkflowState(
                phase=self._phase,
                module_id=binding.module_id if binding else None,
                step_id=binding.step_id if binding else None,
                ticket_id=binding.ticket_id if binding else None,
                attempt=binding.attempt if binding else None,
                prior_period_id=self._case["prior_period_id"],
                current_period_id=self._case["current_period_id"],
                outcome=self._outcome,
            )

    def invoke(self, tool_name: str, arguments: dict[str, JsonValue]) -> dict[str, JsonValue]:
        with self._locked():
            self._current()
            if _unresolved(self._store) or self._binding is None:
                raise OwnerError("not_permitted")
            detached = _json_copy(arguments)
            if type(tool_name) is not str or not isinstance(detached, dict):
                raise OwnerError("bad_arguments")
            if isinstance(self._binding, OwnerBinding):
                if self._upstream is None or self._owner_session is None:
                    raise OwnerError("not_permitted")
                calls = _records(self._store, "owner-calls", OwnerToolCall)
                if (
                    sum(c.receipt.binding.ticket_id == self._binding.ticket_id for c in calls)
                    >= MAX_OWNER_CALLS
                ):
                    raise OwnerError("transport_limit")
                receipt = _parse(OwnerToolReceipt, self._upstream.invoke(tool_name, detached))
                if receipt.binding != self._binding:
                    raise OwnerError("identity_mismatch")
                record = OwnerToolCall(
                    ordinal=len(calls) + 1,
                    session_id=self._owner_session.session_id,
                    receipt=receipt,
                )
                self._current()
                _retain(self._store, "owner-calls", record)
                result = receipt.model_dump(mode="json")
            else:
                if self._source is None or self._phase not in _SOURCE_PHASES:
                    raise OwnerError("not_permitted")
                foundation_calls = _records(self._store, "foundation-calls", FinancialCall)
                if (
                    sum(
                        c.binding.ticket_id == self._binding.ticket_id
                        and c.binding.step_id == self._binding.step_id
                        for c in foundation_calls
                    )
                    >= MAX_FOUNDATION
                ):
                    raise OwnerError("transport_limit")
                source_receipt = _parse(FinancialCall, self._source.invoke(tool_name, detached))
                if source_receipt.binding != self._binding:
                    raise OwnerError("identity_mismatch")
                self._current()
                _retain(self._store, "foundation-calls", source_receipt)
                result = source_receipt.model_dump(mode="json")
            self._current()
            return result

    def read_inputs(self) -> InputRead | OwnerAccessRead:
        with self._locked():
            self._current()
            if _unresolved(self._store) or self._binding is None:
                raise OwnerError("not_permitted")
            record: InputRead | OwnerAccessRead
            if isinstance(self._binding, OwnerBinding):
                if self._upstream is None or self._owner_session is None:
                    raise OwnerError("not_permitted")
                reads = tuple(
                    r
                    for r in _records(self._store, "owner-reads", OwnerAccessRead)
                    if r.session_id == self._owner_session.session_id
                )
                if len(reads) >= MAX_ACCESS_READS:
                    raise OwnerError("transport_limit")
                header = _canonical(self._upstream.access_manifest)
                if header != self._owner_session.access_manifest_json:
                    raise OwnerError("identity_mismatch")
                record = OwnerAccessRead(
                    session_id=self._owner_session.session_id,
                    sequence=len(reads) + 1,
                    binding=self._binding,
                    access_manifest_json=header,
                )
                kind = "owner-reads"
            else:
                if self._phase not in {"narrative", "readiness", "quality"}:
                    raise OwnerError("not_permitted")
                foundation_reads = tuple(
                    r
                    for r in _records(self._store, "foundation-reads", InputRead)
                    if r.binding.ticket_id == self._binding.ticket_id
                    and r.binding.step_id == self._binding.step_id
                )
                if len(foundation_reads) >= MAX_FOUNDATION:
                    raise OwnerError("transport_limit")
                digest, body = _projection(self._store, self._binding)
                record = InputRead(
                    binding=self._binding,
                    sequence=1 + sum(r.binding == self._binding for r in foundation_reads),
                    inputs_sha256=digest,
                    body=body,
                )
                kind = "foundation-reads"
            self._current()
            _retain(self._store, kind, record)
            self._current()
            return record

    def _advance(self, outcome: SubmissionOutcome, bound: BoundSubmission) -> None:
        snapshot = self._store.read()
        self._current_sha256 = snapshot.content_hash()
        attempt = next(a for a in snapshot.attempts if a.ticket_id == bound.binding.ticket_id)
        if outcome.disposition == "refused":
            if isinstance(bound.binding, OwnerBinding) and self._upstream is None:
                # Reopen deliberately cannot restore an opaque nonce. Once the
                # old intent is resolved, persist a fresh actual session; the
                # old intent keeps its original selected ID and captured prefix.
                self._activate(attempt, "earnings_delta")
            elif (
                isinstance(bound.binding, FinancialBinding)
                and bound.binding.step_id in _SOURCE_PHASES
                and self._source is None
            ):
                self._activate(attempt, bound.binding.step_id, replay=True)
            return
        if outcome.disposition == "valid" and bound.binding.step_id == "earnings_delta":
            self._phase, self._outcome, self._binding = "complete", "owner_settled", None
            return
        if outcome.disposition == "valid" and bound.binding.step_id in {
            "source_readiness",
            "quality",
        }:
            module_id = "CP-1" if bound.binding.step_id == "source_readiness" else "CP-1B"
            if module_id == "CP-1B":
                candidate = _cp1_candidate(self._store, snapshot, attempt)
                if candidate.content_hash() != attempt.payload_sha256:
                    raise OwnerError("identity_mismatch")
                head = next(h for h in snapshot.heads if h.module_id == "CP-1")
                _preflight(
                    _FrozenExecution(self._store, snapshot).head_module(head),
                    self._case["prior_period_id"],
                    self._case["current_period_id"],
                )
            next_attempt = self._begin(module_id)
            if next_attempt is not None:
                self._activate(
                    next_attempt, "source_context" if module_id == "CP-1" else "earnings_delta"
                )
        elif attempt.status == "pending":
            phase = (
                CP1_PROMOTION[len(attempt.steps)]
                if outcome.disposition == "valid"
                else bound.binding.step_id
            )
            self._activate(attempt, phase)
        elif attempt.number == 0:
            next_attempt = self._begin(attempt.module_id)
            if next_attempt is None:
                raise OwnerError("identity_mismatch")
            phase = (
                "source_readiness"
                if attempt.module_id == "CP-0"
                else "earnings_delta"
                if attempt.module_id == "CP-1B"
                else "source_context"
            )
            self._activate(next_attempt, phase)
        else:
            self._phase, self._outcome, self._binding = "failed", None, None

    def submit_review(self, payload: str) -> ReviewOutcome:
        with self._locked():
            self._current()
            if self._binding is None or type(payload) is not str:
                raise OwnerError("not_permitted")
            try:
                raw = payload.encode("utf-8")
            except UnicodeEncodeError:
                raise OwnerError("bad_arguments") from None
            if len(raw) > MAX_LINE:
                raise OwnerError("transport_limit")
            if _text_depth(payload) >= MAX_JSON_DEPTH:
                # Refused before any audit write: a payload that cannot be parsed
                # or ruled on must not leave an orphan record without an intent.
                raise OwnerError("bad_arguments")
            pending = _unresolved(self._store)
            if pending:
                intent = pending[0]
                if _hash(raw) != intent.binding.raw_payload_sha256:
                    raise OwnerError("identity_mismatch")
                bound = intent.binding
            else:
                intents = _records(self._store, "intents", SubmissionIntent)
                scoped = [
                    i
                    for i in intents
                    if i.binding.binding.ticket_id == self._binding.ticket_id
                    and i.binding.binding.step_id == self._binding.step_id
                ]
                if len(scoped) >= MAX_FOUNDATION:
                    raise OwnerError("transport_limit")
                bound, _ = _prepare_bound(self._store, self._binding, payload, self._owner_session)
                _retain(self._store, "bindings", bound)
                intent = SubmissionIntent(
                    index=len(intents) + 1,
                    binding=bound,
                    snapshot_before_sha256=self._binding.snapshot_sha256,
                )
                self._current()
                _retain(self._store, "intents", intent)
            outcome = _complete_intent(self._store, intent)
            self._advance(outcome, bound)
            errors = (
                ()
                if outcome.disposition == "valid"
                else tuple(
                    dict.fromkeys(
                        issue
                        if issue in _ERRORS
                        else "participation_incomplete"
                        if outcome.disposition == "refused"
                        else "validation_failed"
                        for issue in outcome.issues
                    )
                )
            )
            return ReviewOutcome(
                module_id=bound.binding.module_id,
                step_id=bound.binding.step_id,
                ticket_id=bound.binding.ticket_id,
                attempt=bound.binding.attempt,
                disposition=outcome.disposition,
                issue_count=len(outcome.issues),
                error_codes=errors,
                snapshot_sha256=self._current_sha256,
                next_phase=self._phase,
                stored_payload_sha256=bound.stored_payload_sha256,
            )

    def write_receipt(self, destination: Path) -> EarningsOwnerReceipt:
        with self._locked():
            snapshot = self._current()
            if self._phase != "complete" or self._outcome is None or _unresolved(self._store):
                raise OwnerError("not_permitted")
            fields = _transcript_fields(self._store)
            positive = self._outcome == "owner_settled"
            cp0 = _head_record(self._store, snapshot, "CP-0")
            cp1 = _head_record(self._store, snapshot, "CP-1") if positive else None
            cp1b = _head_record(self._store, snapshot, "CP-1B") if positive else None
            stage_hash = None
            if cp1b is not None:
                attempt = next(a for a in snapshot.attempts if a.ticket_id == cp1b.ticket_id)
                stage_hash = attempt.steps[0].output_sha256
            receipt = EarningsOwnerReceipt(
                run=snapshot.run,
                pack_sha256=snapshot.pack_sha256,
                owner_snapshot_sha256=snapshot.content_hash(),
                case_id=self._setup_record.case_id,
                pins=self._setup_record.pins,
                participant=self._setup_record.participant,
                transport=self._setup_record.transport,
                outcome=self._outcome,
                cp0=cp0,
                cp1=cp1,
                cp1b=cp1b,
                cp1b_stage_sha256=stage_hash,
                **fields,
                audit_inventory=_inventory(self._store),
                publication_files=(),
            )
            if len(receipt.model_dump_json().encode()) > MAX_RECEIPT:
                raise OwnerError("transport_limit")
            _verify_owner(self._store, receipt, sealed=False)
            self._current()
            raw = receipt.model_dump_json().encode()
            root = self._store.directory / "earnings-owner-audit"
            # `owner-receipt.sha256` is the only commit point. A `owner-receipt.json` left
            # without it by a crash is uncommitted: the newly verified receipt replaces it,
            # and so does a destination holding exactly those uncommitted bytes.
            pending = root / "owner-receipt.json"
            uncommitted = pending.read_bytes() if pending.exists() else None
            if destination.exists():
                exported = destination.read_bytes()
                if exported != raw and (
                    exported != uncommitted or not _earlier_receipt(exported, receipt)
                ):
                    raise OwnerError("identity_mismatch")
                if exported != raw:
                    destination.unlink()
            pending.unlink(missing_ok=True)
            _put(root / "owner-receipt.json", raw)
            _put(destination, raw)
            self._current()
            _put(root / "owner-receipt.sha256", receipt.content_hash().encode("ascii"))
            self._current()
            self._sealed = True
            return receipt


_Operation = Literal["state", "invoke", "read_inputs", "submit_review", "close", "invalid"]


def _classify_frame(raw: bytes) -> tuple[_Operation, dict[str, Any] | None, str | None]:
    if not raw or len(raw) > MAX_LINE + 1:
        raise OwnerError("identity_mismatch")
    if len(raw) == MAX_LINE + 1:
        return "invalid", None, "transport_limit"
    if not raw.endswith(b"\n"):
        return "invalid", None, "bad_arguments"

    def nonfinite(_value: str) -> None:
        raise ValueError("nonfinite JSON")

    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), parse_constant=nonfinite)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return "invalid", None, "bad_arguments"
    if type(value) is not dict or type(value.get("op")) is not str:
        return "invalid", None, "bad_arguments"
    operation = value["op"]
    keys = {
        "state": {"op"},
        "invoke": {"op", "tool", "arguments"},
        "read_inputs": {"op"},
        "submit_review": {"op", "payload"},
        "close": {"op"},
    }
    if operation not in keys:
        return "invalid", None, "not_permitted"
    if set(value) != keys[operation]:
        return "invalid", None, "bad_arguments"
    if operation == "invoke" and (
        type(value["tool"]) is not str or type(value["arguments"]) is not dict
    ):
        return "invalid", None, "bad_arguments"
    if operation == "submit_review" and type(value["payload"]) is not str:
        return "invalid", None, "bad_arguments"
    try:
        _json_copy(value)
    except OwnerError:
        return "invalid", None, "bad_arguments"
    return cast(_Operation, operation), value, None


def _write_reply(writer: TextIO, value: JsonObject) -> None:
    raw = (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8", errors="strict")
    written = writer.buffer.write(raw)
    if type(written) is not int or written != len(raw):
        raise OSError("Incomplete binary transport reply")
    writer.buffer.flush()


def serve_json_lines(
    workflow: EarningsWorkflow, reader: TextIO, writer: TextIO, *, destination: Path
) -> None:
    """Capture exact bounded raw frames before dispatch; use buffers exclusively."""
    if not isinstance(reader, io.TextIOWrapper) or not isinstance(writer, io.TextIOWrapper):
        raise OwnerError("bad_arguments")
    try:
        if (
            reader.closed
            or writer.closed
            or reader.buffer.closed
            or writer.buffer.closed
            or not reader.buffer.readable()
            or not writer.buffer.writable()
        ):
            raise OwnerError("bad_arguments")
    except (AttributeError, ValueError):
        raise OwnerError("bad_arguments") from None
    if workflow._setup_record.transport != "bounded-json-lines/1":
        raise OwnerError("not_permitted")
    if not workflow._dispatcher.acquire(blocking=False):
        raise OwnerError("not_permitted")
    try:
        while True:
            with workflow._locked():
                workflow._current()
                messages = _records(workflow._store, "transport-messages", TransportMessage)
                exhausted = len(messages) >= MAX_MESSAGES
            if exhausted:
                _write_reply(writer, {"status": "refused", "error_code": "transport_limit"})
                return
            raw = reader.buffer.readline(MAX_LINE + 1)
            if not raw:
                return
            if type(raw) is not bytes:
                raise TypeError("Binary transport reader did not return bytes")
            with workflow._locked():
                workflow._current()
                request_hash = _payload(workflow._store, raw)
                operation, request, error = _classify_frame(raw)
                messages = _records(workflow._store, "transport-messages", TransportMessage)
                if len(messages) >= MAX_MESSAGES:
                    raise OwnerError("transport_limit")
                message = TransportMessage(
                    index=len(messages) + 1, operation=operation, request_sha256=request_hash
                )
                _retain(workflow._store, "transport-messages", message)
            closed = False
            if error is not None:
                reply: JsonObject = {"status": "refused", "error_code": error}
            else:
                if request is None:
                    raise OwnerError("internal_error")
                try:
                    if operation == "state":
                        result = workflow.state().model_dump(mode="json")
                    elif operation == "invoke":
                        result = workflow.invoke(request["tool"], request["arguments"])
                    elif operation == "read_inputs":
                        result = workflow.read_inputs().model_dump(mode="json")
                    elif operation == "submit_review":
                        result = workflow.submit_review(request["payload"]).model_dump(mode="json")
                    elif operation == "close":
                        receipt = workflow.write_receipt(destination)
                        result = OwnerClose(
                            outcome=receipt.outcome,
                            owner_receipt_sha256=receipt.content_hash(),
                            owner_snapshot_sha256=receipt.owner_snapshot_sha256,
                        ).model_dump(mode="json")
                        closed = True
                    else:
                        raise OwnerError("not_permitted")
                    reply = {"status": "ok", "result": result}
                except OwnerError as refused:
                    reply = {"status": "refused", "error_code": refused.code}
            _write_reply(writer, reply)
            if closed or len(raw) == MAX_LINE + 1 or not raw.endswith(b"\n"):
                return
    finally:
        workflow._dispatcher.release()
