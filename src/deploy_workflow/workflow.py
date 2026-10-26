"""Finite source-readiness workflow and offline JSON-lines analytical transport.

Execution owns validation/settlement. This bridge adds evidence gates and finite,
hash-addressed audit records, never accepts caller-built Modules or authority.
"""

import argparse
import hashlib
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Literal, TextIO

from pydantic import BaseModel, ValidationError

from deploy_vii.contracts import Contract, Hash, Identifier, Input, Run
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.cp1_workflow import submit_cp1_step, validate_cp1_stage
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    NotAuthorized,
    current_inputs,
)
from deploy_vii.live.tools import Seen, ToolRules
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import ReadinessReview, build_readiness
from deploy_vii.source_context import SourceContextReport, SourceContextReview
from deploy_workflow.host import SourceSession
from deploy_workflow.tools.source import SourceError

MAX_CALLS_PER_STEP = 16
MAX_MESSAGES = 64
MAX_LINE = 1024 * 1024


class WorkflowError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class SessionBinding(Contract):
    run_id: Identifier
    issuer_id: Identifier
    as_of: str
    method_version: str
    pack_sha256: Hash
    snapshot_sha256: Hash
    module_id: Literal["CP-0", "CP-1"]
    step_id: Literal["source_readiness", "source_context"]
    ticket_id: Identifier
    attempt: int
    inputs: tuple[Input, ...]


class SourceEvidence(Contract):
    read: tuple[tuple[str, str], ...] = ()
    extracted: tuple[tuple[str, str], ...] = ()
    surfaced: tuple[tuple[str, str], ...] = ()
    searched: tuple[str | None, ...] = ()

    def seen(self) -> Seen:
        return Seen(frozenset((*self.read, *self.extracted)), self.searched)


class ToolCall(Contract):
    schema_version: Literal["tool-receipt/1"]
    call_id: str
    sequence: int
    binding: SessionBinding
    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "refused", "error"]
    body: str | None
    error_code: str | None
    source_evidence: SourceEvidence


class SubmissionBinding(Contract):
    schema_version: Literal["submission-binding/1"]
    binding: SessionBinding
    payload_sha256: Hash
    successful_call_ids: tuple[str, ...]
    call_ids: tuple[str, ...]
    source_evidence: SourceEvidence


class ReviewSubmission(Contract):
    module_id: Literal["CP-0", "CP-1"]
    step_id: Literal["source_readiness", "source_context"]
    ticket_id: Identifier
    payload_sha256: Hash
    canonical_review_sha256: Hash | None
    binding_sha256: Hash
    binding: SubmissionBinding
    disposition: Literal["valid", "invalid", "refused"]
    snapshot_before_sha256: Hash
    snapshot_after_sha256: Hash


class SettledReadiness(Contract):
    ticket_id: Identifier
    attempt: int
    inputs: tuple[Input, ...]
    status: Literal["accepted", "restricted"]
    raw_payload_sha256: Hash
    canonical_review_sha256: Hash
    step_sha256: Hash
    step_output_sha256: Hash
    result_sha256: Hash


class SourceConsumer(Contract):
    ticket_id: Identifier
    attempt: int
    inputs: tuple[Input, ...]
    status: Literal["pending"]
    selected_cp0_sha256: Hash
    raw_payload_sha256: Hash
    canonical_review_sha256: Hash
    step_sha256: Hash
    step_output_sha256: Hash
    output_status: Literal["candidate", "restricted"]


class SourceSliceReceipt(Contract):
    schema_version: Literal["source-slice-receipt/1"] = "source-slice-receipt/1"
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    participant: str
    transport: Literal["python-api", "bounded-json-lines/1"]
    calls: tuple[ToolCall, ...]
    submissions: tuple[ReviewSubmission, ...]
    cp0: SettledReadiness
    cp1: SourceConsumer | None
    cp1_refusal: Literal["not_authorized"] | None


def _parse[T: BaseModel](model: type[T], value: Any) -> T:
    return model.model_validate_json(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _digest(raw: bytes) -> str:
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
    return store.directory / "source-slice-audit" / kind / digest


def _read_audit(store: Execution, kind: str, digest: str) -> bytes:
    raw = _audit(store, kind, digest).read_bytes()
    if _digest(raw) != digest:
        raise WorkflowError("identity_mismatch")
    return raw


def _canonical(step_id: str, payload: str) -> str | None:
    try:
        model = ReadinessReview if step_id == "source_readiness" else SourceContextReview
        return model.model_validate_json(payload).content_hash()
    except ValidationError:
        return None


def _snapshot(store: Execution, digest: str) -> ExecutionSnapshot:
    raw = (store.directory / "snapshots" / (digest + ".json")).read_bytes()
    snapshot = ExecutionSnapshot.model_validate_json(raw)
    if _digest(raw) != digest or snapshot.content_hash() != digest:
        raise WorkflowError("identity_mismatch")
    return snapshot


def _historical(store: Execution, binding: SessionBinding) -> ExecutionSnapshot:
    snapshot = _snapshot(store, binding.snapshot_sha256)
    pack = store.pack(snapshot)
    run = snapshot.run
    attempts = [a for a in snapshot.attempts if a.ticket_id == binding.ticket_id]
    if (
        len(attempts) != 1
        or attempts[0].status != "pending"
        or attempts[0].module_id != binding.module_id
        or attempts[0].number != binding.attempt
        or attempts[0].inputs != binding.inputs
        or current_inputs(snapshot, binding.module_id) != binding.inputs
        or (
            run.run_id,
            run.issuer_id,
            run.as_of.isoformat(),
            run.method_version,
            pack.content_hash(),
        )
        != (
            binding.run_id,
            binding.issuer_id,
            binding.as_of,
            binding.method_version,
            binding.pack_sha256,
        )
    ):
        raise WorkflowError("identity_mismatch")
    return snapshot


def _selected(store: Execution, snapshot: ExecutionSnapshot, cp0_ticket: str) -> SettledReadiness:
    attempts = [a for a in snapshot.attempts if a.ticket_id == cp0_ticket]
    heads = [h for h in snapshot.heads if h.module_id == "CP-0"]
    if len(attempts) != 1 or len(heads) != 1:
        raise WorkflowError("identity_mismatch")
    attempt = attempts[0]
    if (
        attempt.module_id != "CP-0"
        or attempt.status != "finished"
        or attempt.issues
        or len(attempt.steps) != 1
    ):
        raise WorkflowError("identity_mismatch")
    step = attempt.steps[0]
    if step.step_id != "source_readiness" or step.status != "valid" or step.output_sha256 is None:
        raise WorkflowError("identity_mismatch")
    raw = store.payload(step.payload_sha256)
    review = ReadinessReview.model_validate_json(raw)
    candidate = build_readiness(store.pack(snapshot), review, attempt=attempt.number)
    if (
        candidate.content_hash() != step.output_sha256
        or store.step_output(step.output_sha256) != candidate.model_dump_json()
    ):
        raise WorkflowError("identity_mismatch")
    result = store.head_module(heads[0])
    if (
        attempt.result_sha256 != heads[0].result_sha256
        or result.status not in ("accepted", "restricted")
        or result.model_copy(update={"status": "candidate", "inherited_limitations": ()})
        != candidate
    ):
        raise WorkflowError("identity_mismatch")
    return _parse(
        SettledReadiness,
        {
            "ticket_id": attempt.ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in result.inputs],
            "status": result.status,
            "raw_payload_sha256": step.payload_sha256,
            "canonical_review_sha256": review.content_hash(),
            "step_sha256": step.content_hash(),
            "step_output_sha256": step.output_sha256,
            "result_sha256": heads[0].result_sha256,
        },
    )


def _consumer(
    store: Execution, snapshot: ExecutionSnapshot, cp0: SettledReadiness
) -> SourceConsumer | None:
    attempts = [a for a in snapshot.attempts if a.module_id == "CP-1"]
    if not attempts:
        try:
            current_inputs(snapshot, "CP-1")
        except NotAuthorized:
            return None
        raise WorkflowError("identity_mismatch")
    if len(attempts) != 1 or any(h.module_id != "CP-0" for h in snapshot.heads):
        raise WorkflowError("identity_mismatch")
    attempt = attempts[0]
    if (
        attempt.status != "pending"
        or attempt.payload_sha256 is not None
        or attempt.result_sha256 is not None
        or len(attempt.steps) != 1
    ):
        raise WorkflowError("identity_mismatch")
    step = attempt.steps[0]
    if step.step_id != "source_context" or step.status != "valid" or step.output_sha256 is None:
        raise WorkflowError("identity_mismatch")
    if attempt.inputs != current_inputs(snapshot, "CP-1") or not any(
        i.input_id == "CP-0" and i.sha256 == cp0.result_sha256 and i.status == cp0.status
        for i in attempt.inputs
    ):
        raise WorkflowError("identity_mismatch")
    outcome = validate_cp1_stage(store, store.pack(snapshot), attempt)
    if outcome.issues or not outcome.retained_as(step):
        raise WorkflowError("identity_mismatch")
    output = SourceContextReport.model_validate_json(store.step_output(step.output_sha256))
    review = SourceContextReview.model_validate_json(store.payload(step.payload_sha256))
    if (
        output.run != snapshot.run
        or output.pack_sha256 != snapshot.pack_sha256
        or output.context_review_sha256 != review.content_hash()
    ):
        raise WorkflowError("identity_mismatch")
    return _parse(
        SourceConsumer,
        {
            "ticket_id": attempt.ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
            "status": attempt.status,
            "selected_cp0_sha256": cp0.result_sha256,
            "raw_payload_sha256": step.payload_sha256,
            "canonical_review_sha256": review.content_hash(),
            "step_sha256": step.content_hash(),
            "step_output_sha256": step.output_sha256,
            "output_status": output.status,
        },
    )


def _verify(store: Execution, receipt: SourceSliceReceipt, *, sealed: bool) -> None:
    snapshot = store.read()
    pack = store.pack(snapshot)
    if (
        snapshot.content_hash() != receipt.snapshot_sha256
        or snapshot.run != receipt.run
        or pack.content_hash() != receipt.pack_sha256
    ):
        raise WorkflowError("stale_binding")
    if (
        sealed
        and (store.directory / "source-slice-audit" / "receipt.sha256").read_text()
        != receipt.content_hash()
    ):
        raise WorkflowError("identity_mismatch")
    cp0 = _selected(store, snapshot, receipt.cp0.ticket_id)
    cp1 = _consumer(store, snapshot, cp0)
    if (
        receipt.cp0 != cp0
        or receipt.cp1 != cp1
        or receipt.cp1_refusal != (None if cp1 else "not_authorized")
    ):
        raise WorkflowError("identity_mismatch")
    calls = {c.call_id: c for c in receipt.calls}
    if len(calls) != len(receipt.calls):
        raise WorkflowError("identity_mismatch")
    for call in receipt.calls:
        if _read_audit(store, "calls", call.content_hash()) != call.model_dump_json().encode():
            raise WorkflowError("identity_mismatch")
        historical = _historical(store, call.binding)
        if historical.run != receipt.run or historical.pack_sha256 != receipt.pack_sha256:
            raise WorkflowError("identity_mismatch")
    for submission in receipt.submissions:
        raw = _read_audit(store, "payloads", submission.payload_sha256).decode("utf-8")
        binding = submission.binding
        if (
            _read_audit(store, "bindings", submission.binding_sha256)
            != binding.model_dump_json().encode()
            or binding.payload_sha256 != submission.payload_sha256
            or (
                None if submission.disposition == "refused" else _canonical(submission.step_id, raw)
            )
            != submission.canonical_review_sha256
            or binding.binding.module_id != submission.module_id
            or binding.binding.step_id != submission.step_id
            or binding.binding.ticket_id != submission.ticket_id
            or binding.binding.snapshot_sha256 != submission.snapshot_before_sha256
        ):
            raise WorkflowError("identity_mismatch")
        _historical(store, binding.binding)
        after = _snapshot(store, submission.snapshot_after_sha256)
        if after.run != receipt.run or store.pack(after).content_hash() != receipt.pack_sha256:
            raise WorkflowError("identity_mismatch")
        if submission.disposition == "valid":
            post_ticket = [a for a in after.attempts if a.ticket_id == submission.ticket_id]
            final_ticket = [a for a in snapshot.attempts if a.ticket_id == submission.ticket_id]
            if (
                len(post_ticket) != 1
                or post_ticket != final_ticket
                or after.heads != snapshot.heads
            ):
                raise WorkflowError("identity_mismatch")
            if submission.module_id == "CP-0":
                if any(a.module_id == "CP-1" for a in after.attempts):
                    raise WorkflowError("identity_mismatch")
            elif after.content_hash() != receipt.snapshot_sha256:
                raise WorkflowError("identity_mismatch")
        scoped = [c for c in receipt.calls if c.binding == binding.binding]
        prefix = scoped[: len(binding.call_ids)]
        if (
            tuple(c.call_id for c in prefix) != binding.call_ids
            or tuple(c.call_id for c in prefix if c.status == "ok") != binding.successful_call_ids
            or (prefix[-1].source_evidence if prefix else SourceEvidence())
            != binding.source_evidence
        ):
            raise WorkflowError("identity_mismatch")
        issues = ToolRules().issues(
            submission.step_id, raw, seen=binding.source_evidence.seen(), context=None
        )
        if submission.disposition == "refused":
            if not issues or submission.snapshot_before_sha256 != submission.snapshot_after_sha256:
                raise WorkflowError("identity_mismatch")
        elif submission.disposition == "valid":
            expected = cp0 if submission.module_id == "CP-0" else cp1
            if (
                issues
                or expected is None
                or expected.raw_payload_sha256 != submission.payload_sha256
                or expected.ticket_id != submission.ticket_id
            ):
                raise WorkflowError("identity_mismatch")
        else:
            raise WorkflowError("identity_mismatch")
    valid = [s.module_id for s in receipt.submissions if s.disposition == "valid"]
    if valid != (["CP-0", "CP-1"] if cp1 else ["CP-0"]):
        raise WorkflowError("identity_mismatch")
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise WorkflowError("stale_binding")


def verify_source_slice_receipt(store: Execution, receipt: SourceSliceReceipt) -> None:
    """Authenticate a receipt against immutable audit bytes and actual journal coordinates."""
    try:
        _verify(store, receipt, sealed=True)
    except WorkflowError:
        raise
    except (ValueError, OSError, KeyError, UnicodeError):
        raise WorkflowError("identity_mismatch") from None


class SourceWorkflow:
    def __init__(self, store: Execution, attempt: Attempt) -> None:
        self._store = store
        self._cp0_ticket = attempt.ticket_id
        self._operation = Lock()
        self._calls: list[ToolCall] = []
        self._submissions: list[ReviewSubmission] = []
        self._done = False
        self._cp1_refusal: Literal["not_authorized"] | None = None
        self._participant = "trusted-python"
        self._transport: Literal["python-api", "bounded-json-lines/1"] = "python-api"
        self._activate(attempt, "source_readiness")

    @classmethod
    def create(cls, directory: Path, pack: PreparedPack) -> "SourceWorkflow":
        if pack.run.requested_modules != ("CP-1",):
            raise WorkflowError("not_permitted")
        store = Execution.create(directory, pack)
        return cls(store, store.begin("CP-0"))

    def _activate(self, attempt: Attempt, step_id: str) -> None:
        self._session = SourceSession.from_execution(self._store, attempt.ticket_id, step_id)
        self._epoch = _parse(SubmissionBinding, self._session.bind_submission("")).binding
        self._current_sha256 = self._epoch.snapshot_sha256
        self._epoch_calls: list[ToolCall] = []
        self._attempted_calls = 0

    @contextmanager
    def _locked(self) -> Iterator[None]:
        if not self._operation.acquire(blocking=False):
            raise WorkflowError("not_permitted")
        try:
            yield
        finally:
            self._operation.release()

    def _current(self) -> ExecutionSnapshot:
        snapshot = self._store.read()
        if snapshot.content_hash() != self._current_sha256:
            raise WorkflowError("stale_binding")
        self._store.pack(snapshot)
        return snapshot

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            self._current()
            if self._done or self._attempted_calls >= MAX_CALLS_PER_STEP:
                raise WorkflowError("not_permitted")
            self._attempted_calls += 1
            result = self._session.invoke(tool_name, arguments)
            call = _parse(ToolCall, result)
            if call.binding != self._epoch or call.sequence != len(self._epoch_calls) + 1:
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "calls", call.content_hash()), call.model_dump_json().encode())
            self._epoch_calls.append(call)
            self._calls.append(call)
            return result

    def submit_review(self, payload: str) -> dict[str, Any]:
        with self._locked():
            before = self._current()
            if self._done or type(payload) is not str:
                raise WorkflowError("not_permitted")
            binding = _parse(SubmissionBinding, self._session.bind_submission(payload))
            payload_bytes = payload.encode()
            expected_evidence = (
                self._epoch_calls[-1].source_evidence if self._epoch_calls else SourceEvidence()
            )
            if (
                binding.binding != self._epoch
                or binding.payload_sha256 != _digest(payload_bytes)
                or binding.call_ids != tuple(c.call_id for c in self._epoch_calls)
                or binding.successful_call_ids
                != tuple(c.call_id for c in self._epoch_calls if c.status == "ok")
                or binding.source_evidence != expected_evidence
            ):
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "payloads", binding.payload_sha256), payload_bytes)
            _put(
                _audit(self._store, "bindings", binding.content_hash()),
                binding.model_dump_json().encode(),
            )
            issues = ToolRules().issues(
                self._epoch.step_id, payload, seen=binding.source_evidence.seen(), context=None
            )
            self._current()
            module, step_id, ticket = (
                self._epoch.module_id,
                self._epoch.step_id,
                self._epoch.ticket_id,
            )
            if issues:
                disposition = "refused"
                validation_issues = issues
            else:
                attempt = (
                    submit_cp0_review(self._store, ticket, payload)
                    if module == "CP-0"
                    else submit_cp1_step(self._store, ticket, step_id, payload)
                )
                disposition = (
                    "valid"
                    if not attempt.issues and attempt.steps and attempt.steps[-1].status == "valid"
                    else "invalid"
                )
                validation_issues = attempt.issues
                if disposition == "invalid" and not validation_issues:
                    rejected = [
                        s
                        for s in (*attempt.steps, *attempt.step_repairs)
                        if s.step_id == step_id
                        and s.status == "invalid"
                        and s.payload_sha256 == binding.payload_sha256
                    ]
                    if len(rejected) != 1:
                        raise WorkflowError("identity_mismatch")
                    validation_issues = rejected[0].issues
            after = self._store.read()
            record = _parse(
                ReviewSubmission,
                {
                    "module_id": module,
                    "step_id": step_id,
                    "ticket_id": ticket,
                    "payload_sha256": binding.payload_sha256,
                    "canonical_review_sha256": None
                    if disposition == "refused"
                    else _canonical(step_id, payload),
                    "binding_sha256": binding.content_hash(),
                    "binding": binding.model_dump(mode="json"),
                    "disposition": disposition,
                    "snapshot_before_sha256": before.content_hash(),
                    "snapshot_after_sha256": after.content_hash(),
                },
            )
            self._submissions.append(record)
            self._current_sha256 = after.content_hash()
            if disposition == "valid" and module == "CP-0":
                try:
                    self._activate(self._store.begin("CP-1"), "source_context")
                except NotAuthorized:
                    self._cp1_refusal = "not_authorized"
                    self._done = True
            elif disposition == "valid" or disposition == "invalid":
                self._done = True
            return {
                "schema_version": "review-outcome/1",
                "status": disposition,
                "error_code": "evidence_refused"
                if issues
                else "validation_failed"
                if disposition == "invalid"
                else None,
                "issue_count": len(validation_issues),
                "module_id": module,
                "step_id": step_id,
                "ticket_id": ticket,
                "snapshot_sha256": self._current_sha256,
                "cp1_refusal": self._cp1_refusal,
            }

    def write_receipt(self, destination: Path) -> SourceSliceReceipt:
        with self._locked():
            snapshot = self._current()
            if not self._done:
                raise WorkflowError("not_permitted")
            cp0 = _selected(self._store, snapshot, self._cp0_ticket)
            cp1 = _consumer(self._store, snapshot, cp0)
            receipt = _parse(
                SourceSliceReceipt,
                {
                    "run": snapshot.run.model_dump(mode="json"),
                    "pack_sha256": snapshot.pack_sha256,
                    "snapshot_sha256": snapshot.content_hash(),
                    "participant": self._participant,
                    "transport": self._transport,
                    "calls": [c.model_dump(mode="json") for c in self._calls],
                    "submissions": [s.model_dump(mode="json") for s in self._submissions],
                    "cp0": cp0.model_dump(mode="json"),
                    "cp1": None if cp1 is None else cp1.model_dump(mode="json"),
                    "cp1_refusal": self._cp1_refusal,
                },
            )
            _verify(self._store, receipt, sealed=False)
            self._current()
            _put(
                self._store.directory / "source-slice-audit" / "receipt.sha256",
                receipt.content_hash().encode(),
            )
            _put(destination, receipt.model_dump_json().encode())
            self._current()
            return receipt


def serve_json_lines(
    workflow: SourceWorkflow, reader: TextIO, writer: TextIO, *, destination: Path, participant: str
) -> None:
    if workflow._calls or workflow._submissions:
        raise WorkflowError("not_permitted")
    workflow._participant = participant
    workflow._transport = "bounded-json-lines/1"
    for _ in range(MAX_MESSAGES):
        line = reader.readline(MAX_LINE + 1)
        if not line:
            return
        try:
            if len(line) > MAX_LINE:
                while line and not line.endswith("\n"):
                    line = reader.readline(MAX_LINE + 1)
                raise WorkflowError("bad_arguments")
            request = json.loads(line)
            if type(request) is not dict:
                raise WorkflowError("bad_arguments")
            operation = request.get("operation")
            if operation == "invoke" and set(request) == {"operation", "tool", "arguments"}:
                result = workflow.invoke(request["tool"], request["arguments"])
            elif operation == "submit_review" and set(request) == {"operation", "payload"}:
                result = workflow.submit_review(request["payload"])
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
        except Exception:  # noqa: BLE001 - bounded transport never exposes internal diagnostics.
            result = {"status": "error", "error_code": "internal_error"}
        writer.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
        writer.flush()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finite offline source workflow; trusted setup paths."
    )
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--participant", required=True)
    args = parser.parse_args()
    pack = PreparedPack.model_validate_json(args.pack.read_bytes())
    workflow = SourceWorkflow.create(args.directory, pack)
    serve_json_lines(
        workflow, sys.stdin, sys.stdout, destination=args.receipt, participant=args.participant
    )


if __name__ == "__main__":
    main()
