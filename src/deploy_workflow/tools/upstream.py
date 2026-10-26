"""Bounded, source-free CP1 lookup and read-only verification (Task0 v1)."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from threading import Lock
from typing import Any
from uuid import uuid4

from deploy_vii import cp5_integrity
from deploy_vii.business_context import referencable
from deploy_vii.contracts import Fact, Module
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, current_inputs
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import citation_issues
from deploy_vii.registry import dependencies, step_chain

_VIEWS = {"CP-2": "credit_synthesis", "CP-5": "integrity_review"}
_KEYS = frozenset(
    {
        "fact_id",
        "label",
        "table_id",
        "row_id",
        "field",
        "amount",
        "text",
        "status",
        "unit",
        "currency",
        "scale",
        "period",
        "basis",
        "denominator",
        "limitation",
        "calculation_id",
        "value_class",
        "calculation_status",
        "citation_handles",
    }
)
_IDENTITY_KEYS = frozenset({"fact_id", "table_id", "row_id", "field", "status"})
_INTERNAL_GRANT = (
    "all metadata/citations of the single bound CP-1 artifact; no raw/quote disclosure"
)
_LOOKUP_KEYS = {"producer_module_id", "producer_sha256", "table_id", "row_ids", "fields"}
_VERIFY_KEYS = {"producer_module_id", "producer_sha256", "kind", "fact_ids"}


class _Refusal(ValueError):
    """An intentional refusal containing a public category and no private diagnostics."""


@dataclass(frozen=True)
class _Grants:
    producers: frozenset[str]
    tables: frozenset[str]
    rows: frozenset[str]
    fields: frozenset[str]
    coordinates: frozenset[str]
    integrity: bool

    def admits(self, fact: Fact) -> bool:
        return (
            fact.table_id in self.tables
            and fact.row_id in self.rows
            and fact.field in self.coordinates
        )


def _strings(value: object, maximum: int) -> list[str]:
    if (
        type(value) is not list
        or not 1 <= len(value) <= maximum
        or any(type(item) is not str or not item for item in value)
    ):
        raise _Refusal("bad_arguments")
    if len(set(value)) != len(value):
        raise _Refusal("bad_arguments")
    return value


def _view(module_id: str, producer: Module) -> tuple[Fact, ...]:
    # CP5's canonical/status view is explicitly adopted by Task0, separately from
    # integrity_projection (which would omit clean facts not named by any claim).
    return producer.facts if module_id == "CP-5" else referencable(producer.facts)


def _grants(value: Mapping[str, Any], module_id: str, producer: Module) -> _Grants:
    keys = {
        "producer_ids",
        "table_ids",
        "row_ids",
        "fields",
        "fact_fields",
        "raw_source_ids",
        "integrity_internal_inspection",
    }
    if not isinstance(value, Mapping) or set(value) - keys or value.get("raw_source_ids", []) != []:
        raise _Refusal("not_permitted")
    groups = {}
    for name in ("producer_ids", "table_ids", "row_ids", "fields", "fact_fields"):
        groups[name] = frozenset(_strings(value.get(name), 100_000))
    facts = _view(module_id, producer)
    allowed = {
        "producer_ids": {"CP-1"},
        "fields": _KEYS,
        "table_ids": {fact.table_id for fact in facts},
        "row_ids": {fact.row_id for fact in facts},
        "fact_fields": {fact.field for fact in facts},
    }
    if any(not group <= allowed[name] for name, group in groups.items()):
        raise _Refusal("not_permitted")
    internal = value.get("integrity_internal_inspection")
    if internal is not None and internal != _INTERNAL_GRANT:
        raise _Refusal("not_permitted")
    return _Grants(
        producers=groups["producer_ids"],
        tables=groups["table_ids"],
        rows=groups["row_ids"],
        fields=groups["fields"],
        coordinates=groups["fact_fields"],
        integrity=module_id == "CP-5" and internal == _INTERNAL_GRANT,
    )


def _context(
    store: Execution, ticket_id: str, step_id: str
) -> tuple[ExecutionSnapshot, Attempt, PreparedPack, dict[str, Module]]:
    snapshot = store.read()
    matches = (item for item in snapshot.attempts if item.ticket_id == ticket_id)
    attempt = next(matches, None)
    if attempt is None or next(matches, None) is not None:
        raise _Refusal("stale_binding")
    if attempt.module_id not in _VIEWS or _VIEWS[attempt.module_id] != step_id:
        raise _Refusal("not_permitted")
    chain = step_chain(attempt.module_id)
    # Both admitted v1 consumers have one settling step, with no in-attempt
    # repair. A retained pending/invalid/valid output cannot admit new tool use.
    if (
        chain.steps != (step_id,)
        or attempt.status != "pending"
        or attempt.steps
        or attempt.step_repairs
        or attempt.payload_sha256 is not None
    ):
        raise _Refusal("stale_binding")
    pack = store.pack(snapshot)
    current = current_inputs(snapshot, attempt.module_id)
    if current != attempt.inputs:
        old = {item.input_id: item for item in attempt.inputs}
        if any(
            item.input_id in old
            and old[item.input_id].sha256 == item.sha256
            and old[item.input_id].status != item.status
            for item in current
        ):
            raise _Refusal("identity_mismatch")
        raise _Refusal("stale_binding")
    selected = dependencies(snapshot.run.requested_modules)
    heads = {head.module_id: head for head in snapshot.heads}
    if len(heads) != len(snapshot.heads) or len({i.input_id for i in attempt.inputs}) != len(
        attempt.inputs
    ):
        raise _Refusal("identity_mismatch")
    modules = {}
    for item in attempt.inputs:
        if item.input_id == "prepared-pack":
            if item.sha256 != pack.content_hash() or item.status != "accepted":
                raise _Refusal("identity_mismatch")
            continue
        if item.input_id not in selected:
            raise _Refusal("not_permitted")
        head = heads.get(item.input_id)
        if head is None or head.status == "stale" or head.result_sha256 != item.sha256:
            raise _Refusal("stale_binding")
        if head.status != item.status:
            raise _Refusal("identity_mismatch")
        module = store.head_module(head)
        run = snapshot.run
        if (
            (module.run_id, module.issuer_id, module.as_of, module.method_version)
            != (run.run_id, run.issuer_id, run.as_of, run.method_version)
            or module.module_id != item.input_id
            or module.status != item.status
            or module.content_hash() != item.sha256
        ):
            raise _Refusal("identity_mismatch")
        modules[item.input_id] = module
    if "CP-1" not in modules:
        raise _Refusal("not_permitted")
    return snapshot, attempt, pack, modules


class UpstreamTools:
    """Single-writer session; authority is frozen by from_execution, not tool arguments.

    Factory refusals raise ValueError with a stable category only. Each invocation
    returns a detached JSON receipt; receipts are retained in call order. v1 does
    not promise durable receipt persistence or analytical submission/settlement.
    """

    def __init__(
        self, store: Execution, ticket_id: str, step_id: str, *, grants: Mapping[str, Any]
    ) -> None:
        try:
            snapshot, attempt, pack, modules = _context(store, ticket_id, step_id)
            granted = _grants(grants, attempt.module_id, modules["CP-1"])
            if store.read().content_hash() != snapshot.content_hash():
                raise _Refusal("stale_binding")
        except _Refusal:
            raise
        except (ValueError, OSError, KeyError, TypeError):
            raise ValueError("identity_mismatch") from None
        self._store = store
        self._attempt = attempt
        self._step_id = step_id
        self._snapshot_sha256 = snapshot.content_hash()
        self._granted = granted
        self._binding = {
            "run_id": snapshot.run.run_id,
            "issuer_id": snapshot.run.issuer_id,
            "as_of": snapshot.run.as_of.isoformat(),
            "method_version": snapshot.run.method_version,
            "pack_sha256": pack.content_hash(),
            "snapshot_sha256": self._snapshot_sha256,
            "module_id": attempt.module_id,
            "step_id": step_id,
            "ticket_id": ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
        }
        self._sequence = 0
        self._lock = Lock()
        self._receipt_lock = Lock()
        self._receipts: list[str] = []

    @classmethod
    def from_execution(
        cls, store: Execution, ticket_id: str, step_id: str, *, grants: Mapping[str, Any]
    ) -> UpstreamTools:
        return cls(store, ticket_id, step_id, grants=grants)

    @property
    def receipts(self) -> tuple[dict[str, Any], ...]:
        """Detached snapshots for the downstream host to bind and retain."""
        with self._receipt_lock:
            decoded = [json.loads(receipt) for receipt in self._receipts]
            return tuple(sorted(decoded, key=lambda receipt: receipt["sequence"]))

    def _current(self) -> tuple[PreparedPack, dict[str, Module]]:
        if self._store.read().content_hash() != self._snapshot_sha256:
            raise _Refusal("stale_binding")
        try:
            snapshot, attempt, pack, modules = _context(
                self._store,
                self._attempt.ticket_id,
                self._step_id,
            )
        except _Refusal:
            raise
        except (ValueError, OSError, KeyError, TypeError):
            raise _Refusal("identity_mismatch") from None
        if snapshot.content_hash() != self._snapshot_sha256 or attempt != self._attempt:
            raise _Refusal("stale_binding")
        return pack, modules

    def _producer(self, args: dict[str, Any], modules: dict[str, Module]) -> Module:
        name, digest = args["producer_module_id"], args["producer_sha256"]
        if (
            type(name) is not str
            or type(digest) is not str
            or re.fullmatch("[0-9a-f]{64}", digest) is None
        ):
            raise _Refusal("bad_arguments")
        if name not in self._granted.producers or name not in modules:
            raise _Refusal("not_permitted")
        producer = modules[name]
        if producer.content_hash() != digest:
            raise _Refusal("identity_mismatch")
        if producer.status not in {"accepted", "restricted"}:
            raise _Refusal("not_permitted")
        return producer

    def _facts(self, producer: Module) -> tuple[Fact, ...]:
        return tuple(
            fact for fact in _view(self._attempt.module_id, producer) if self._granted.admits(fact)
        )

    def _lookup(self, args: dict[str, Any], producer: Module) -> dict[str, Any]:
        rows = _strings(args["row_ids"], 20)
        fields = _strings(args["fields"], 16)
        if not _IDENTITY_KEYS <= set(fields):
            raise _Refusal("bad_arguments")
        table = args["table_id"]
        if type(table) is not str or not table:
            raise _Refusal("bad_arguments")
        if (
            table not in self._granted.tables
            or not set(fields) <= self._granted.fields
            or not set(rows) <= self._granted.rows
        ):
            raise _Refusal("not_permitted")
        available: dict[str, list[Fact]] = {}
        for fact in self._facts(producer):
            if fact.table_id == table:
                available.setdefault(fact.row_id, []).append(fact)
        if not set(rows) <= available.keys():
            raise _Refusal("not_permitted")

        def project(fact: Fact) -> dict[str, Any]:
            data = fact.model_dump(mode="json", include=set(fields) - {"citation_handles"})
            return {
                key: (
                    [
                        {
                            "source_id": c.source_id,
                            "source_sha256": c.source_sha256,
                            "locator": c.locator,
                        }
                        for c in fact.citations
                    ]
                    if key == "citation_handles"
                    else data[key]
                )
                for key in fields
            }

        return {
            "table_id": table,
            "rows": [
                {"row_id": row, "facts": [project(fact) for fact in available[row]]} for row in rows
            ],
        }

    def _verify(self, args: dict[str, Any], producer: Module, pack: PreparedPack) -> dict[str, Any]:
        ids = _strings(args["fact_ids"], 20)
        kind = args["kind"]
        if kind not in ("citations", "integrity"):
            raise _Refusal("bad_arguments")
        permitted = {fact.fact_id: fact for fact in self._facts(producer)}
        if not set(ids) <= permitted.keys():
            raise _Refusal("not_permitted")
        issues: list[dict[str, Any]] = []
        if kind == "citations":
            for fact_id in ids:
                # Diagnostics contain quote prefixes and must never enter receipts.
                failures = citation_issues(permitted[fact_id].citations, pack.sources)
                issues.extend({"code": "fact_citation", "fact_ids": [fact_id]} for _ in failures)
        else:
            if self._attempt.module_id != "CP-5" or not self._granted.integrity:
                raise _Refusal("not_permitted")
            scope = cp5_integrity.review_scope(self._store, self._attempt)
            if scope.issues:
                raise _Refusal("stale_binding")
            if (
                scope.blocked
                or len(scope.evaluated) != 1
                or len(scope.heads) != 1
                or scope.evaluated[0] != producer
                or producer.claims
                or not all(self._granted.admits(fact) for fact in producer.facts)
                or set(ids) != {fact.fact_id for fact in producer.facts}
            ):
                raise _Refusal("not_permitted")
            checks = cp5_integrity.python_checks(scope)
            for finding in checks.findings:
                if finding.kind not in {"fact_citation", "scale_unit", "figure_identity"}:
                    raise RuntimeError("unsupported verification category")
                # Fact-only v1 findings are keyed by 'fact <id>'. A wider finding
                # whose safe exact affected IDs cannot be resolved must fail closed.
                if finding.kind == "figure_identity":
                    matches = [group for group in checks.groups if group.subject == finding.subject]
                    affected = {
                        ref
                        for group in matches
                        for owner, ref in group.members
                        if owner == producer.module_id
                    }
                else:
                    affected = {finding.subject.removeprefix("fact ")}
                if not affected or not affected <= set(ids):
                    raise RuntimeError("unresolvable verification references")
                issues.append(
                    {"code": finding.kind, "fact_ids": [ref for ref in ids if ref in affected]}
                )
        return {
            "kind": kind,
            "verdict": "invalid" if issues else "valid",
            "issue_count": len(issues),
            "issues": issues,
        }

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return and retain one atomic receipt; a failed call has no partial body."""
        # Only JSON-compatible arguments are in the public protocol. Validate
        # before copying so non-JSON objects cannot invoke deepcopy hooks.
        try:
            encoded = json.dumps(arguments, ensure_ascii=False, allow_nan=False)
            supplied = json.loads(encoded)
            del encoded
        except (TypeError, ValueError, RecursionError):
            raise ValueError("bad_arguments") from None
        acquired = self._lock.acquire(blocking=False)
        try:
            with self._receipt_lock:
                self._sequence += 1
                sequence = self._sequence
            receipt: dict[str, Any] = {
                "schema_version": "tool-receipt/1",
                "call_id": str(uuid4()),
                "sequence": sequence,
                "binding": copy.deepcopy(self._binding),
                "tool": tool_name,
                "arguments": supplied,
                "status": "refused",
                "body": None,
                "error_code": None,
                "source_evidence": {"read": [], "extracted": [], "surfaced": [], "searched": []},
            }
            try:
                if not acquired:
                    raise _Refusal("not_permitted")
                expected = {"lookup_upstream": _LOOKUP_KEYS, "verify_upstream": _VERIFY_KEYS}
                if tool_name not in expected:
                    raise _Refusal("not_permitted")
                if type(supplied) is not dict or set(supplied) != expected[tool_name]:
                    raise _Refusal("bad_arguments")
                pack, modules = self._current()
                producer = self._producer(supplied, modules)
                data = (
                    self._lookup(supplied, producer)
                    if tool_name == "lookup_upstream"
                    else self._verify(supplied, producer, pack)
                )
                body = {
                    "producer": {
                        "module_id": producer.module_id,
                        "sha256": producer.content_hash(),
                        "status": producer.status,
                    },
                    **data,
                }
                if len(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()) > 8192:
                    raise _Refusal("bad_arguments")
                # Recheck bytes and authorization, not just a mutable current pointer.
                self._current()
                if self._store.read().content_hash() != self._snapshot_sha256:
                    raise _Refusal("stale_binding")
                receipt.update(status="ok", body=body)
            except _Refusal as refusal:
                receipt["error_code"] = str(refusal)
            except Exception:  # noqa: BLE001 -- sanitize unexpected errors at receipt boundary
                receipt.update(status="error", error_code="internal_error")
            except BaseException:
                # Preserve interruption semantics while retaining a valid failed
                # attempt receipt; never report process control as a tool success.
                receipt.update(status="error", error_code="internal_error")
                raise
            finally:
                with self._receipt_lock:
                    self._receipts.append(
                        json.dumps(
                            receipt, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                        )
                    )
            return receipt
        finally:
            if acquired:
                self._lock.release()
