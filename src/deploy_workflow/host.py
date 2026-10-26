"""Task0 v1 single-writer source host; no submission validation or settlement."""

import json
from hashlib import sha256
from threading import Lock
from typing import Any, cast
from uuid import uuid4

from deploy_vii.contracts import Input
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, current_inputs
from deploy_vii.live.context import declared_sources, readable_sources
from deploy_vii.live.prompts import PromptError
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import step_chain
from deploy_workflow.tools.source import SourceError, SourceTools

_SOURCE_STEPS = {"CP-0": ("source_readiness",), "CP-1": ("source_context", "financials")}


def _detached(value: dict[str, Any]) -> dict[str, Any]:
    """Copy a JSON value without deepcopy's extra Python frames per nested object."""
    return cast(dict[str, Any], json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False)))


def _step_inputs(attempt: Attempt, preceding: tuple[Any, ...]) -> tuple[Input, ...]:
    return (
        *attempt.inputs,
        *(Input(input_id="step:" + step.step_id, sha256=step.content_hash()) for step in preceding),
    )


def _execution_state(
    store: Execution,
    ticket_id: str,
    step_id: str,
) -> tuple[ExecutionSnapshot, Attempt, PreparedPack, tuple[str, ...]]:
    """Check authority and every selected blob before exposing any source capability."""
    try:
        snapshot = store.read()
        tickets = [a for a in snapshot.attempts if a.ticket_id == ticket_id]
        if len(tickets) != 1:
            raise SourceError("not_permitted")
        attempt = tickets[0]
        pending = (
            attempt.status == "pending"
            and attempt.payload_sha256 is None
            and attempt.result_sha256 is None
            and attempt.interruption is None
            and not attempt.issues
        )
        if not pending:
            raise SourceError("not_permitted")
        if step_id not in _SOURCE_STEPS.get(attempt.module_id, ()):
            raise SourceError("not_permitted")
        chain = step_chain(attempt.module_id)
        if step_id not in chain.pack_sources:
            raise SourceError("not_permitted")
        prior_steps = attempt.steps
        ordered_prefix = tuple(s.step_id for s in prior_steps) == chain.steps[: len(prior_steps)]
        all_valid = all(s.status == "valid" for s in prior_steps)
        if (
            not all_valid
            or not ordered_prefix
            or len(prior_steps) >= len(chain.steps)
            or chain.steps[len(prior_steps)] != step_id
        ):
            raise SourceError("not_permitted")
        if sum(a.status == "pending" for a in snapshot.attempts) != 1:
            raise SourceError("identity_mismatch")
        if current_inputs(snapshot, attempt.module_id) != attempt.inputs:
            raise SourceError("identity_mismatch")
        if len({i.input_id for i in attempt.inputs}) != len(attempt.inputs):
            raise SourceError("identity_mismatch")
        pack = store.pack(snapshot)
        if pack.run != snapshot.run or pack.content_hash() != snapshot.pack_sha256:
            raise SourceError("identity_mismatch")
        heads = {h.module_id: h for h in snapshot.heads}
        if len(heads) != len(snapshot.heads):
            raise SourceError("identity_mismatch")
        run = snapshot.run
        for bound in attempt.inputs:
            if bound.input_id == "prepared-pack":
                if bound.sha256 != snapshot.pack_sha256 or bound.status != "accepted":
                    raise SourceError("identity_mismatch")
                continue
            head = heads[bound.input_id]
            producer = store.head_module(head)
            same_head = (head.result_sha256, head.status) == (bound.sha256, bound.status)
            same_run = (
                producer.run_id,
                producer.issuer_id,
                producer.as_of,
                producer.method_version,
            ) == (run.run_id, run.issuer_id, run.as_of, run.method_version)
            if (
                not same_head
                or not same_run
                or producer.inputs != current_inputs(snapshot, producer.module_id)
            ):
                raise SourceError("identity_mismatch")
        for index, step in enumerate(prior_steps):
            if step.inputs != _step_inputs(attempt, prior_steps[:index]):
                raise SourceError("identity_mismatch")
            if step.output_sha256 is None:
                raise SourceError("identity_mismatch")
            store.payload(step.payload_sha256)
            store.step_output(step.output_sha256)
        for repair in attempt.step_repairs:
            if repair.step_id not in chain.repairable:
                raise SourceError("not_permitted")
            index = chain.steps.index(repair.step_id)
            if index > len(prior_steps):
                raise SourceError("not_permitted")
            if repair.inputs != _step_inputs(attempt, prior_steps[:index]):
                raise SourceError("identity_mismatch")
            store.payload(repair.payload_sha256)
            if repair.output_sha256 is not None:
                store.step_output(repair.output_sha256)
        if attempt.number == 0:
            if attempt.repair_of is not None:
                raise SourceError("identity_mismatch")
        else:
            previous = [a for a in snapshot.attempts if a.ticket_id == attempt.repair_of]
            if (
                len(previous) != 1
                or previous[0].status != "finished"
                or not previous[0].issues
                or previous[0].module_id != attempt.module_id
                or previous[0].number != 0
                or previous[0].inputs != attempt.inputs
            ):
                raise SourceError("identity_mismatch")
        ids = tuple(s.source_id for s in pack.sources)
        declared = set(declared_sources(store, attempt, step_id, ids))
        readable = set(readable_sources(store, attempt, step_id))
        if not declared <= set(ids) or not readable <= set(ids):
            raise SourceError("identity_mismatch")
        sources = tuple(ident for ident in ids if ident in declared and ident in readable)
        if store.read().content_hash() != snapshot.content_hash():
            raise SourceError("stale_binding")
        return snapshot, attempt, pack, sources
    except SourceError:
        raise
    except (ValueError, KeyError, OSError):
        raise SourceError("identity_mismatch") from None


def _json_arguments(arguments: Any) -> dict[str, Any]:
    """JSON input must round-trip without coercing tuples, keys or numeric sentinels."""

    def check(value: Any) -> None:
        if type(value) in (str, int, float, bool, type(None)):
            return
        if type(value) is list:
            for item in value:
                check(item)
            return
        if type(value) is dict and all(type(key) is str for key in value):
            for item in value.values():
                check(item)
            return
        raise ValueError("not JSON")

    if type(arguments) is not dict:
        raise ValueError("arguments must be an object")
    check(arguments)
    return _detached(arguments)


class SourceSession:
    """Trusted factory pins authority; analytical callers can only invoke or bind bytes."""

    def __init__(
        self,
        store: Execution,
        snapshot: ExecutionSnapshot,
        attempt: Attempt,
        step_id: str,
        pack: PreparedPack,
        sources: tuple[str, ...],
    ) -> None:
        self._store = store
        self._ticket_id = attempt.ticket_id
        self._step_id = step_id
        self._snapshot_sha256 = snapshot.content_hash()
        run = snapshot.run
        self._binding = {
            "run_id": run.run_id,
            "issuer_id": run.issuer_id,
            "as_of": run.as_of.isoformat(),
            "method_version": run.method_version,
            "pack_sha256": pack.content_hash(),
            "snapshot_sha256": self._snapshot_sha256,
            "module_id": attempt.module_id,
            "step_id": step_id,
            "ticket_id": attempt.ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
        }
        self._tools = SourceTools(pack, sources, extraction=step_id == "financials")
        self._operation = Lock()
        self._records_lock = Lock()
        self._sequence = 0
        self._calls: dict[int, dict[str, Any]] = {}

    @classmethod
    def from_execution(cls, store: Execution, ticket_id: str, step_id: str) -> "SourceSession":
        snapshot, attempt, pack, sources = _execution_state(store, ticket_id, step_id)
        return cls(store, snapshot, attempt, step_id, pack, sources)

    def _assert_current(self) -> None:
        try:
            if self._store.read().content_hash() != self._snapshot_sha256:
                raise SourceError("stale_binding")
            snapshot, _, _, _ = _execution_state(self._store, self._ticket_id, self._step_id)
            if snapshot.content_hash() != self._snapshot_sha256:
                raise SourceError("stale_binding")
        except SourceError:
            raise
        except (ValueError, OSError):
            raise SourceError("identity_mismatch") from None

    def _receipt(
        self,
        sequence: int,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        status: str,
        body: str | None,
        code: str | None,
    ) -> dict[str, Any]:
        receipt = {
            "schema_version": "tool-receipt/1",
            "call_id": call_id,
            "sequence": sequence,
            "binding": _detached(self._binding),
            "tool": name,
            "arguments": arguments,
            "status": status,
            "body": body,
            "error_code": code,
            "source_evidence": self._tools.evidence(),
        }
        with self._records_lock:
            self._calls[sequence] = _detached(receipt)
        return _detached(receipt)

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._records_lock:
            self._sequence += 1
            sequence = self._sequence
        call_id = str(uuid4())
        name = tool_name if type(tool_name) is str else ""
        try:
            copied = _json_arguments(arguments)
        except (ValueError, TypeError, RecursionError):
            return self._receipt(sequence, call_id, name, {}, "refused", None, "bad_arguments")
        if not self._operation.acquire(blocking=False):
            return self._receipt(sequence, call_id, name, copied, "refused", None, "not_permitted")
        try:
            self._assert_current()
            body, staged = self._tools.stage(name, copied)
            self._assert_current()
            self._tools.commit(staged)
            return self._receipt(sequence, call_id, name, copied, "ok", body, None)
        except SourceError as error:
            return self._receipt(sequence, call_id, name, copied, "refused", None, error.code)
        except PromptError:
            return self._receipt(sequence, call_id, name, copied, "refused", None, "render_refused")
        except Exception:  # noqa: BLE001 - Task0 requires sanitized unexpected local errors.
            return self._receipt(sequence, call_id, name, copied, "error", None, "internal_error")
        finally:
            self._operation.release()

    def bind_submission(self, payload: str) -> dict[str, Any]:
        if not self._operation.acquire(blocking=False):
            raise SourceError("not_permitted")
        try:
            self._assert_current()
            if type(payload) is not str:
                raise SourceError("bad_arguments")
            try:
                digest = sha256(payload.encode("utf-8")).hexdigest()
            except UnicodeError:
                raise SourceError("bad_arguments") from None
            with self._records_lock:
                calls = [self._calls[index] for index in sorted(self._calls)]
                record = {
                    "schema_version": "submission-binding/1",
                    "binding": _detached(self._binding),
                    "payload_sha256": digest,
                    "successful_call_ids": [c["call_id"] for c in calls if c["status"] == "ok"],
                    "call_ids": [c["call_id"] for c in calls],
                    "source_evidence": self._tools.evidence(),
                }
            self._assert_current()
            return record
        finally:
            self._operation.release()
