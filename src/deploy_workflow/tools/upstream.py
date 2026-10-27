"""Bounded, source-free CP1 lookup and read-only verification (Task0 v1)."""

from __future__ import annotations

import copy
import hashlib
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

_VIEWS = {"CP-2": "credit_synthesis", "CP-5": "integrity_review", "CP-1B": "earnings_delta"}
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
    exact: frozenset[tuple[str, str, str, str]] | None = None

    def admits(self, fact: Fact) -> bool:
        if self.exact is not None:
            return _coordinate(fact) in self.exact
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
    return producer.facts if module_id in {"CP-5", "CP-1B"} else referencable(producer.facts)


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


_V2_SCHEMA = "cp1b-upstream-grant/2"
_V2_REQUIRED = _KEYS - {"denominator", "value_class", "calculation_status"}
_COORD_KEYS = ("fact_id", "table_id", "row_id", "field")
_PAGE_KEYS = {"producer_module_id", "producer_sha256", "manifest_sha256", "cursor", "limit"}
_MEASURES = frozenset({
    "revenue", "ebitda", "adjusted_ebitda", "ebitda_margin", "cfo_reported", "capex",
    "fcf", "cash_closing", "total_debt", "net_debt", "total_leverage_reported",
    "net_leverage_reported",
})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _coordinate(fact: Fact) -> tuple[str, str, str, str]:
    return (fact.fact_id, fact.table_id, fact.row_id, fact.field)


def _historical_fields(producer: Module) -> tuple[set[tuple[str, str, str, str]], set[str]]:
    """Resolve identities, not dates, labels, values or a second financial model."""
    index: dict[str, dict[str, Fact]] = {}
    for fact in producer.facts:
        if fact.table_id == "T4.14":
            index.setdefault(fact.row_id, {})[fact.field] = fact
    if not index:
        raise _Refusal("not_permitted")
    identities: set[str] = set()
    fields: set[str] = set()
    for row in index.values():
        if not {"period_id", "period_type"} <= row.keys():
            raise _Refusal("not_permitted")
        identity, kind = row["period_id"], row["period_type"]
        if any(f.status != "known" or not f.text or f.amount is not None
               for f in (identity, kind)):
            raise _Refusal("not_permitted")
        pid = identity.text
        assert pid is not None  # The known-text guard above also rejects empty identities.
        if pid in identities or any(f.period != pid for f in row.values()):
            raise _Refusal("identity_mismatch")
        identities.add(pid)
        if kind.text in {"QUARTER", "FY"}:
            column = ("Q:" if kind.text == "QUARTER" else "FY:") + pid
            raw = "".join(f"{len(p)}:{p}" for p in ("historical", column))
            fields.add("model-basis:" + hashlib.sha256(raw.encode()).hexdigest())
    return {_coordinate(f) for row in index.values() for f in row.values()}, fields


def _v2_grants(value: Mapping[str, Any], producer: Module) -> tuple[_Grants, dict[str, Any]]:
    """Validate a detached exact-tuple grant before normalizing or disclosing it."""
    try:
        grant = json.loads(_canonical(value))
    except (ValueError, TypeError, RecursionError):
        raise _Refusal("bad_arguments") from None
    if type(grant) is not dict or set(grant) != {
        "schema_version", "consumer_module_id", "step_id", "producers", "raw_source_ids"
    }:
        raise _Refusal("bad_arguments")
    if (grant["schema_version"] != _V2_SCHEMA or grant["consumer_module_id"] != "CP-1B"
            or grant["step_id"] != "earnings_delta" or grant["raw_source_ids"] != []):
        raise _Refusal("not_permitted")
    entries = grant["producers"]
    if type(entries) is not list or not entries:
        raise _Refusal("bad_arguments")
    if len(entries) != 1:
        raise _Refusal("not_permitted")
    entry = entries[0]
    if type(entry) is not dict or set(entry) != {
        "module_id", "sha256", "coordinates", "projected_fields"
    }:
        raise _Refusal("bad_arguments")
    if entry["module_id"] != "CP-1":
        raise _Refusal("not_permitted")
    if type(entry["sha256"]) is not str or re.fullmatch("[0-9a-f]{64}", entry["sha256"]) is None:
        raise _Refusal("bad_arguments")
    if producer.content_hash() != entry["sha256"]:
        raise _Refusal("identity_mismatch")
    if producer.status not in {"accepted", "restricted"}:
        raise _Refusal("not_permitted")
    fields = frozenset(_strings(entry["projected_fields"], len(_KEYS)))
    if not _V2_REQUIRED <= fields or not fields <= _KEYS:
        raise _Refusal("not_permitted")
    coords = entry["coordinates"]
    if type(coords) is not list or not 1 <= len(coords) <= 100_000:
        raise _Refusal("bad_arguments")
    selected: set[tuple[str, str, str, str]] = set()
    ids: set[str] = set()
    placements: set[tuple[str, str, str]] = set()
    coordinate_keys = set(_COORD_KEYS)
    for coord in coords:
        if (type(coord) is not dict or coord.keys() != coordinate_keys
                or any(type(coord[k]) is not str or not coord[k] for k in _COORD_KEYS)):
            raise _Refusal("bad_arguments")
        key = tuple(coord[k] for k in _COORD_KEYS)
        placement = key[1:]
        if key in selected or key[0] in ids or placement in placements:
            raise _Refusal("bad_arguments")
        selected.add(key)
        ids.add(key[0])
        placements.add(placement)
    actual: set[tuple[str, str, str, str]] = set()
    actual_ids: set[str] = set()
    actual_placements: set[tuple[str, str, str]] = set()
    rows: dict[str, dict[str, Fact]] = {}
    for fact in producer.facts:
        coordinate = _coordinate(fact)
        actual.add(coordinate)
        actual_ids.add(coordinate[0])
        actual_placements.add(coordinate[1:])
        if fact.table_id == "T4.10":
            rows.setdefault(fact.row_id, {})[fact.field] = fact
    fact_count = len(producer.facts)
    if (len(actual) != fact_count or len(actual_ids) != fact_count
            or len(actual_placements) != fact_count):
        raise _Refusal("identity_mismatch")
    index, historical = _historical_fields(producer)
    if not index <= selected or not selected <= actual:
        raise _Refusal("not_permitted")
    names: dict[str, int] = {}
    for row in rows.values():
        metric = row.get("field_1")
        if metric is not None and metric.status == "known" and metric.text in _MEASURES:
            names[metric.text] = names.get(metric.text, 0) + 1
    selected_values = selected - index
    selected_rows = {key[2] for key in selected_values}
    by_row: dict[str, set[tuple[str, str, str, str]]] = {}
    for key in selected_values:
        by_row.setdefault(key[2], set()).add(key)
    allowed_fields = historical | {"field_0", "field_1"}
    for rid in selected_rows:
        row = rows.get(rid, {})
        name = row.get("field_1")
        category = row.get("field_0")
        if (name is None or category is None or name.status != "known"
                or name.text not in _MEASURES or category.status != "known" or not category.text):
            raise _Refusal("not_permitted")
        if names[name.text] != 1:
            raise _Refusal("identity_mismatch")
        own = by_row[rid]
        if (any(key[1] != "T4.10" or key[3] not in allowed_fields for key in own)
                or not {_coordinate(name), _coordinate(category)} <= own
                or not any(key[3] in historical for key in own)):
            raise _Refusal("not_permitted")
    entry["coordinates"] = sorted(coords, key=lambda c: (
        c["table_id"], c["row_id"], c["field"], c["fact_id"]))
    entry["projected_fields"] = sorted(fields)
    return _Grants(frozenset({"CP-1"}), frozenset(k[1] for k in selected),
                   frozenset(k[2] for k in selected), fields,
                   frozenset(k[3] for k in selected), False, frozenset(selected)), grant


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
    if attempt.module_id == "CP-1B":
        current_attempts = [a for a in snapshot.attempts if a.module_id == "CP-1B"]
        if (attempt.interruption is not None or attempt.issues or attempt.result_sha256 is not None
                or current_attempts[-1] != attempt):
            raise _Refusal("stale_binding")
    pack = store.pack(snapshot)
    if attempt.module_id == "CP-1B" and (
        pack.run != snapshot.run or pack.content_hash() != snapshot.pack_sha256
    ):
        raise _Refusal("identity_mismatch")
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
            normalized = None
            if attempt.module_id == "CP-1B":
                if not isinstance(grants, Mapping) or grants.get("schema_version") != _V2_SCHEMA:
                    raise _Refusal("not_permitted")
                granted, normalized = _v2_grants(grants, modules["CP-1"])
            else:
                if isinstance(grants, Mapping) and "schema_version" in grants:
                    raise _Refusal("not_permitted")
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
        self._manifest: dict[str, Any] | None = None
        if normalized is not None:
            try:
                self._make_manifest(normalized, modules["CP-1"])
                self._current()
            except _Refusal:
                raise
            except Exception:
                raise ValueError("internal_error") from None

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

    def _make_manifest(self, normalized: dict[str, Any], producer: Module) -> None:
        coordinates = normalized["producers"][0]["coordinates"]
        self._coordinates = tuple(tuple(c[k] for k in _COORD_KEYS) for c in coordinates)
        self._nonce = uuid4().hex
        self._cursors: dict[str, int] = {}
        periods = [c for c in coordinates if c["table_id"] == "T4.14"]
        header = {
            "schema_version": "cp1b-access-manifest/1",
            "consumer": {"module_id": "CP-1B", "step_id": "earnings_delta"},
            "producer": {"module_id": "CP-1", "sha256": producer.content_hash(),
                         "status": producer.status},
            "snapshot_sha256": self._snapshot_sha256,
            "ticket_id": self._attempt.ticket_id, "attempt": self._attempt.number,
            "grant_sha256": _digest(normalized),
            "period_index": {"table_id": "T4.14", "authorized_complete": True,
                             "row_count": len({c["row_id"] for c in periods}),
                             "coordinate_count": len(periods)},
            "coordinate_count": len(coordinates),
            "projected_fields": sorted(self._granted.fields),
            "max_page_entries": 20, "max_body_bytes": 8192,
        }
        self._manifest = {**header, "manifest_sha256": _digest({
            "header": header, "coordinates": coordinates})}
        if len(_canonical(self._manifest)) > 8192:
            raise _Refusal("bad_arguments")

    @property
    def access_manifest(self) -> dict[str, Any]:
        """Detached bootstrap; completeness describes grants, never observed reads."""
        if self._manifest is None:
            raise _Refusal("not_permitted")
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            raise _Refusal("not_permitted")
        try:
            self._current()
            result: dict[str, Any] = json.loads(_canonical(self._manifest))
            self._current()
            return result
        except _Refusal:
            raise
        except Exception:
            raise ValueError("internal_error") from None
        finally:
            self._lock.release()

    def _manifest_page(
        self, args: dict[str, Any]
    ) -> tuple[dict[str, Any], tuple[str, int] | None]:
        assert self._manifest is not None
        digest, cursor, limit = args["manifest_sha256"], args["cursor"], args["limit"]
        if (type(digest) is not str or re.fullmatch("[0-9a-f]{64}", digest) is None
                or type(limit) is not int or not 1 <= limit <= 20):
            raise _Refusal("bad_arguments")
        if digest != self._manifest["manifest_sha256"]:
            raise _Refusal("identity_mismatch")
        offset = 0
        if cursor is not None:
            if type(cursor) is not str or re.fullmatch("access-cursor:[0-9a-f]{64}", cursor) is None:
                raise _Refusal("bad_arguments")
            if cursor not in self._cursors:
                raise _Refusal("stale_binding")
            offset = self._cursors[cursor]
        total = len(self._coordinates)
        maximum = min(offset + limit, total)
        page_entries = [dict(zip(_COORD_KEYS, c, strict=True))
                        for c in self._coordinates[offset:maximum]]
        body = {
            "producer": dict(self._manifest["producer"]),
            "grant_sha256": self._manifest["grant_sha256"], "manifest_sha256": digest,
            "coordinate_count": total, "offset": offset,
            "entries": page_entries,
            "next_cursor": None, "complete": False,
        }
        for end in range(maximum, offset, -1):
            token = None if end == total else "access-cursor:" + _digest({
                "nonce": self._nonce, "binding": self._binding,
                "manifest_sha256": digest, "offset": end})
            body["next_cursor"] = token
            body["complete"] = end == total
            if len(_canonical(body)) <= 8192:
                return body, None if token is None else (token, end)
            page_entries.pop()
        raise _Refusal("bad_arguments")

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
        if self._manifest is not None and self._store.read().content_hash() != self._snapshot_sha256:
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
        facts = tuple(
            fact for fact in _view(self._attempt.module_id, producer) if self._granted.admits(fact)
        )
        return tuple(sorted(facts, key=lambda f: (f.field, f.fact_id))) if self._manifest else facts

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
            **({"projection": "granted_fact_projection",
                "grant_sha256": self._manifest["grant_sha256"],
                "manifest_sha256": self._manifest["manifest_sha256"]} if self._manifest else {}),
            "table_id": table,
            "rows": [
                {"row_id": row, "facts": [project(fact) for fact in available[row]]} for row in rows
            ],
        }

    def _verify(self, args: dict[str, Any], producer: Module, pack: PreparedPack) -> dict[str, Any]:
        ids = _strings(args["fact_ids"], 20)
        kind = args["kind"]
        if self._manifest is not None and kind == "integrity":
            raise _Refusal("not_permitted")
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
            **({"grant_sha256": self._manifest["grant_sha256"],
                "manifest_sha256": self._manifest["manifest_sha256"]} if self._manifest else {}),
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
            staged_cursor = None
            try:
                if not acquired:
                    raise _Refusal("not_permitted")
                expected = {"lookup_upstream": _LOOKUP_KEYS, "verify_upstream": _VERIFY_KEYS}
                if self._manifest is not None:
                    expected["read_access_manifest"] = _PAGE_KEYS
                if tool_name not in expected:
                    raise _Refusal("not_permitted")
                if type(supplied) is not dict or set(supplied) != expected[tool_name]:
                    raise _Refusal("bad_arguments")
                pack, modules = self._current()
                producer = self._producer(supplied, modules)
                if tool_name == "read_access_manifest":
                    data, staged_cursor = self._manifest_page(supplied)
                elif tool_name == "lookup_upstream":
                    data = self._lookup(supplied, producer)
                else:
                    data = self._verify(supplied, producer, pack)
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
                if receipt["status"] == "ok" and staged_cursor is not None:
                    token, offset = staged_cursor
                    self._cursors[token] = offset
            return receipt
        finally:
            if acquired:
                self._lock.release()
