"""Bounded, source-free CP1 lookup and read-only verification (Task0 v1)."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
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


def _project_fields(fact: Fact, fields: list[str]) -> dict[str, Any]:
    data = fact.model_dump(mode="json", include=set(fields) - {"citation_handles"})
    return {
        key: (
            [{"source_id": c.source_id, "source_sha256": c.source_sha256, "locator": c.locator}
             for c in fact.citations]
            if key == "citation_handles" else data[key]
        )
        for key in fields
    }


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
        if isinstance(grants, Mapping) and grants.get("schema_version") == _INTEGRITY_SCHEMA:
            return _IntegrityTools(store, ticket_id, step_id, grants=grants)
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
        self._projection_cursors: dict[str, int] = {}
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

    def _projection_page(
        self, args: dict[str, Any], producer: Module
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
            if (type(cursor) is not str
                    or re.fullmatch("(?:projection|access)-cursor:[0-9a-f]{64}", cursor) is None):
                raise _Refusal("bad_arguments")
            if cursor not in self._projection_cursors:
                raise _Refusal("stale_binding")
            offset = self._projection_cursors[cursor]
        wanted = set(self._coordinates[offset:offset + limit])
        facts: dict[tuple[str, str, str, str], Fact] = {}
        for fact in producer.facts:
            if self._granted.admits(fact):
                key = _coordinate(fact)
                if key in wanted:
                    facts[key] = fact
        fields = sorted(self._granted.fields)
        total = len(self._coordinates)
        entries: list[dict[str, Any]] = []
        body: dict[str, Any] = {
            "producer": dict(self._manifest["producer"]),
            "projection": "granted_fact_projection",
            "grant_sha256": self._manifest["grant_sha256"], "manifest_sha256": digest,
            "coordinate_count": total, "offset": offset, "entries": entries,
            "next_cursor": None, "complete": False,
        }
        best_end: int | None = None
        best_token: str | None = None
        for end in range(offset + 1, min(offset + limit, total) + 1):
            entries.append(_project_fields(facts[self._coordinates[end - 1]], fields))
            token = None if end == total else "projection-cursor:" + _digest({
                "domain": "projection", "nonce": self._nonce, "binding": self._binding,
                "grant_sha256": self._manifest["grant_sha256"],
                "manifest_sha256": digest, "offset": end})
            body["next_cursor"] = token
            body["complete"] = end == total
            if len(_canonical(body)) <= 8192:
                best_end, best_token = end, token
        if best_end is None:
            raise _Refusal("bad_arguments")
        del entries[best_end - offset:]
        body["next_cursor"] = best_token
        body["complete"] = best_end == total
        return body, None if best_token is None else (best_token, best_end)

    def _retain_projection(self, receipt: dict[str, Any]) -> None:
        """A failed new-tool finalization cannot publish a successful body/cursor."""
        def append_owned(encoded: str) -> None:
            with self._receipt_lock:
                try:
                    self._receipts.append(encoded)
                except BaseException:
                    # The encoded call ID/sequence identifies only this provisional record.
                    for index in range(len(self._receipts) - 1, -1, -1):
                        if self._receipts[index] == encoded:
                            del self._receipts[index]
                    raise

        try:
            encoded = json.dumps(receipt, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            if receipt["status"] == "ok":
                self._current()
            append_owned(encoded)
            return
        except _Refusal as refusal:
            receipt.update(status="refused", error_code=str(refusal), body=None)
        except Exception:
            receipt.update(status="error", error_code="internal_error", body=None)
        try:
            encoded = json.dumps(receipt, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            append_owned(encoded)
        except Exception:
            raise ValueError("internal_error") from None

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

        return {
            **({"projection": "granted_fact_projection",
                "grant_sha256": self._manifest["grant_sha256"],
                "manifest_sha256": self._manifest["manifest_sha256"]} if self._manifest else {}),
            "table_id": table,
            "rows": [
                {"row_id": row, "facts": [_project_fields(fact, fields) for fact in available[row]]}
                for row in rows
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
            try:
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
            except Exception:
                if tool_name == "read_access_projection":
                    raise ValueError("internal_error") from None
                raise
            staged_cursor = None
            cursor_store: dict[str, int] | None = None
            try:
                if not acquired:
                    raise _Refusal("not_permitted")
                expected = {"lookup_upstream": _LOOKUP_KEYS, "verify_upstream": _VERIFY_KEYS}
                if self._manifest is not None:
                    expected["read_access_manifest"] = _PAGE_KEYS
                    expected["read_access_projection"] = _PAGE_KEYS
                if tool_name not in expected:
                    raise _Refusal("not_permitted")
                if type(supplied) is not dict or set(supplied) != expected[tool_name]:
                    raise _Refusal("bad_arguments")
                pack, modules = self._current()
                producer = self._producer(supplied, modules)
                if tool_name == "read_access_manifest":
                    data, staged_cursor = self._manifest_page(supplied)
                    cursor_store = self._cursors
                elif tool_name == "read_access_projection":
                    data, staged_cursor = self._projection_page(supplied, producer)
                    cursor_store = self._projection_cursors
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
                if tool_name == "read_access_projection":
                    self._retain_projection(receipt)
                else:
                    with self._receipt_lock:
                        self._receipts.append(
                            json.dumps(
                                receipt, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                            )
                        )
                if receipt["status"] == "ok" and staged_cursor is not None:
                    assert cursor_store is not None
                    token, offset = staged_cursor
                    cursor_store[token] = offset
            return receipt
        finally:
            if acquired:
                self._lock.release()

# CP5-v2 is deliberately isolated from the previously frozen CP1B/v1 paths.
_INTEGRITY_SCHEMA = 'cp5-upstream-grant/2'
_REQUIRED_SECTIONS = (
    'producers', 'claims', 'claim_citations', 'required_evidence', 'findings',
    'identity_groups', 'unsettled', 'limitations', 'lineage_bundles', 'lineage_headers',
    'lineage_operands', 'lineage_companions', 'lineage_citations', 'lineage_owner_facts',
    'fact_citations',
)
_SECTIONS = (*_REQUIRED_SECTIONS, 'fact_index')
_PYTHON_KINDS = cp5_integrity.KINDS[:8]
_INTEGRITY_LIMITS = {
    'body_bytes': 8192, 'page_entries': 20, 'lookup_rows': 20, 'lookup_fields': 16,
    'verify_fact_ids': 20, 'request_line_bytes': 4194304,
    'tool_operations_per_attempt': 1024, 'messages_per_attempt': 2048,
}
_LINEAGE_MEASURES = (
    'revenue', 'ebitda', 'adjusted_ebitda', 'ebitda_margin', 'cfo_reported', 'capex',
    'fcf', 'cash_closing', 'total_debt', 'net_debt', 'total_leverage_reported',
    'net_leverage_reported',
)
_PERIOD_FIELDS = (
    'period_id', 'period_type', 'fiscal_year', 'fiscal_quarter', 'start_date', 'end_date',
    'currency', 'unit', 'accounting_basis', 'entity_perimeter',
)


@dataclass(frozen=True)
class _Derived:
    """What the current CP1 proves one lineage must contain."""

    primary: dict[str, Fact | None]
    companions: list[Fact]
    identities: dict[str, tuple[str, str | None]]


def _object(value: Any, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise _Refusal('bad_arguments')
    return value


def _hash_string(value: Any) -> str:
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise _Refusal('bad_arguments')
    return value


def _identifier(value: Any) -> str:
    if (type(value) is not str or len(value) > 160
            or re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]*', value) is None):
        raise _Refusal('bad_arguments')
    return value


def _array(value: Any) -> list[Any]:
    if type(value) is not list:
        raise _Refusal('bad_arguments')
    return value


def _unique_array(value: Any) -> list[Any]:
    result = _array(value)
    keys = [_canonical(v) for v in result]
    if len(set(keys)) != len(keys):
        raise _Refusal('bad_arguments')
    return result


def _producer_ref(head: Module) -> dict[str, str]:
    return {'module_id': head.module_id, 'sha256': head.content_hash(), 'status': head.status}


def _handles(fact: Fact) -> list[dict[str, str]]:
    return [{'source_id': c.source_id, 'source_sha256': c.source_sha256, 'locator': c.locator}
            for c in fact.citations]


def _strict_json(raw: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate')
            result[key] = value
        return result
    def nonfinite(_: str) -> None:
        raise ValueError('nonfinite')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def _integrity_grants(
    supplied: Mapping[str, Any], scope: cp5_integrity.ReviewScope,
) -> dict[str, Any]:
    """Require exact complete authority before normalizing any disclosure catalog."""
    try:
        grant = _strict_json(_canonical(supplied).decode())
    except (ValueError, TypeError, RecursionError):
        raise _Refusal('bad_arguments') from None
    grant = _object(grant, {'schema_version', 'consumer_module_id', 'step_id', 'bound_inputs',
                    'producers', 'raw_source_ids', 'internal_scope_inspection'})
    if (grant['schema_version'] != _INTEGRITY_SCHEMA or grant['consumer_module_id'] != 'CP-5'
            or grant['step_id'] != 'integrity_review' or grant['raw_source_ids'] != []
            or grant['internal_scope_inspection']
            != 'complete_bound_scope_for_existing_python_checks_only'):
        raise _Refusal('not_permitted')
    inputs = _unique_array(grant['bound_inputs'])
    for item in inputs:
        _object(item, {'input_id', 'sha256', 'status'})
        _identifier(item['input_id'])
        _hash_string(item['sha256'])
        if type(item['status']) is not str or item['status'] not in {'accepted', 'restricted', 'blocked'}:
            raise _Refusal('bad_arguments')
    if inputs != [i.model_dump(mode='json') for i in scope.inputs]:
        raise _Refusal('identity_mismatch')
    entries = _unique_array(grant['producers'])
    normalized: dict[str, dict[str, Any]] = {}
    for entry in entries:
        _object(entry, {'module_id', 'sha256', 'status', 'role', 'fact_coordinates',
                        'claim_ids', 'claim_citation_refs', 'projected_fact_fields'})
        mid = _identifier(entry['module_id'])
        _hash_string(entry['sha256'])
        if mid in normalized:
            raise _Refusal('bad_arguments')
        if type(entry['status']) is not str or entry['status'] not in {'accepted', 'restricted', 'blocked'}:
            raise _Refusal('bad_arguments')
        if type(entry['role']) is not str or entry['role'] not in {'evaluated', 'blocked'}:
            raise _Refusal('bad_arguments')
        for coord in _unique_array(entry['fact_coordinates']):
            _object(coord, set(_COORD_KEYS))
            for value in coord.values():
                _identifier(value)
        for cid in _unique_array(entry['claim_ids']):
            _identifier(cid)
        for ref in _unique_array(entry['claim_citation_refs']):
            if type(ref) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]*#c[1-9][0-9]*', ref) is None:
                raise _Refusal('bad_arguments')
        fields = _unique_array(entry['projected_fact_fields'])
        if any(type(field) is not str for field in fields):
            raise _Refusal('bad_arguments')
        if set(fields) != _KEYS:
            raise _Refusal('not_permitted')
        normalized[mid] = entry
    actual = {i.input_id: (i, h) for i, h in scope.heads}
    if set(normalized) != set(actual):
        raise _Refusal('not_permitted')
    total = 0
    for mid, (item, head) in actual.items():
        entry = normalized[mid]
        if entry['sha256'] != item.sha256 or entry['status'] != item.status:
            raise _Refusal('identity_mismatch')
        blocked = item.status == 'blocked'
        if entry['role'] != ('blocked' if blocked else 'evaluated'):
            raise _Refusal('not_permitted')
        coords = [] if blocked else [dict(zip(_COORD_KEYS, _coordinate(f), strict=True))
                                     for f in head.facts]
        claims = [] if blocked else [c.claim_id for c in head.claims]
        citations = [] if blocked else [cp5_integrity.citation_ref(c.claim_id, n)
                                        for c in head.claims
                                        for n in range(1, len(c.citations) + 1)]
        if (len({_coordinate(f) for f in head.facts}) != len(head.facts)
                or len({f.fact_id for f in head.facts}) != len(head.facts)
                or len({(f.table_id, f.row_id, f.field) for f in head.facts}) != len(head.facts)
                or len({c.claim_id for c in head.claims}) != len(head.claims)):
            raise _Refusal('identity_mismatch')
        if (set(map(_canonical, entry['fact_coordinates'])) != set(map(_canonical, coords))
                or set(entry['claim_ids']) != set(claims)
                or set(entry['claim_citation_refs']) != set(citations)):
            raise _Refusal('not_permitted')
        entry['fact_coordinates'] = sorted(coords, key=lambda c: (
            c['table_id'], c['row_id'], c['field'], c['fact_id']))
        entry['claim_ids'] = sorted(claims)
        entry['claim_citation_refs'] = citations if blocked else [
            cp5_integrity.citation_ref(c.claim_id, n)
            for c in sorted(head.claims, key=lambda c: c.claim_id)
            for n in range(1, len(c.citations) + 1)]
        entry['projected_fact_fields'] = sorted(_KEYS)
        total += len(coords)
    if total > 100000:
        raise _Refusal('not_permitted')
    grant['producers'] = sorted(normalized.values(), key=lambda e: cp5_integrity._rank(e['module_id']))
    return grant


class _IntegrityCatalog:
    """Pure source-free projections of the full authenticated core review scope."""

    def __init__(self, scope: cp5_integrity.ReviewScope, binding: dict[str, Any],
                 grants: Mapping[str, Any]) -> None:
        from deploy_vii import prose

        # A scope change between _context and review_scope in the factory is a race after
        # currentness was proved, so it is accepted as stale_binding (LEAD ruling, adversary-2 4a).
        if scope.issues:
            raise _Refusal('stale_binding')
        self.scope = scope
        self.grant = _integrity_grants(grants, scope)
        self.grant_sha256 = _digest(self.grant)
        self.heads = {h.module_id: h for _, h in scope.heads}
        self.facts = {(h.module_id, f.fact_id): f for h in scope.evaluated for f in h.facts}
        self.claims = {(h.module_id, c.claim_id): c for h in scope.evaluated for c in h.claims}
        self.checks = cp5_integrity.python_checks(scope)
        self.sections: dict[str, list[dict[str, Any]]] = {s: [] for s in _SECTIONS}
        self.protected: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.citation_sets: dict[tuple[str, str], dict[str, Any]] = {}
        self.descriptor = {
            'projection_policy': 'cp5-safe-scope/1', 'binding': binding,
            'grant_sha256': self.grant_sha256,
            'bound_inputs': [i.model_dump(mode='json') for i in scope.inputs],
            'producers': [{
                'producer': _producer_ref(self.heads[e['module_id']]), 'role': e['role'],
                'coordinate_count': len(e['fact_coordinates']),
                'coordinate_sha256': _digest(e['fact_coordinates']),
                'claim_count': len(e['claim_ids']), 'claims_sha256': _digest(e['claim_ids']),
                'claim_citation_count': len(e['claim_citation_refs']),
                'claim_citations_sha256': _digest(e['claim_citation_refs']),
            } for e in self.grant['producers']],
            'kind_order': list(cp5_integrity.KINDS),
        }
        self.scope_sha256 = _digest(self.descriptor)
        reasons: dict[tuple[str, str], set[str]] = {}
        claim_ids: dict[tuple[str, str], set[str]] = {}
        self.named: dict[tuple[str, str], set[str]] = {}
        for head in scope.evaluated:
            bound = prose.bind(head.facts)
            for claim in sorted(head.claims, key=lambda c: c.claim_id):
                key = head.module_id, claim.claim_id
                ids = {bound[r.text].fact_id for r in prose.tokenize(claim.text)
                       if r.kind != 'text' and r.text in bound}
                self.named[key] = ids
                for fid in ids:
                    fk = head.module_id, fid
                    reasons.setdefault(fk, set()).add('claim_reference')
                    claim_ids.setdefault(fk, set()).add(claim.claim_id)
        for mid, refs in self.checks.ref_marks.items():
            for fid in refs:
                if (mid, fid) in self.facts:
                    reasons.setdefault((mid, fid), set()).add('flagged_fact')
        self.groups: dict[str, dict[str, Any]] = {}
        for ordinal, group in enumerate(self.checks.groups):
            record = {'group_id': 'identity:' + _digest({
                'scope': self.scope_sha256, 'ordinal': ordinal, 'basis': group.basis,
                'members': group.members}), 'basis': group.basis,
                'members': [self.ref(mid, 'fact', fid) for mid, fid in group.members],
                'differing': list(group.differing)}
            self.groups[group.subject] = record
            self.sections['identity_groups'].append(record)
            for member in group.members:
                reasons.setdefault(member, set()).add('identity_member')
        for item in self.checks.unsettled:
            self.sections['unsettled'].append({
                'producer': _producer_ref(self.heads[item.module_id]), 'claim_id': item.claim_id,
                'fact_refs': [self.ref(item.module_id, 'fact', fid) for fid in item.fact_ids],
                'limited': item.limited})
            for fid in item.fact_ids:
                key = item.module_id, fid
                reasons.setdefault(key, set()).add('unsettled_fact')
                claim_ids.setdefault(key, set()).add(item.claim_id)
        self._lineage_catalogs(reasons)
        self.sections['findings'] = self.safe_findings(self.checks.findings)
        # The core marks a claim by its own findings and by flagged facts it names
        # (cp5_integrity._Checker.claim/identity); reuse those marks, never re-derive them.
        touching: dict[tuple[str, str], set[str]] = {
            key: {kind for mark in marks for kind in _PYTHON_KINDS
                  if mark.startswith((kind + ':', kind + ' on '))}
            for key, marks in self.checks.claim_marks.items()}
        for entry in self.grant['producers']:
            head = self.heads[entry['module_id']]
            evaluated = entry['role'] == 'evaluated'
            producer = _producer_ref(head)
            self.sections['producers'].append({
                'producer': producer, 'role': entry['role'],
                'fact_count': len(entry['fact_coordinates']), 'claim_count': len(entry['claim_ids']),
                'claim_citation_count': len(entry['claim_citation_refs'])})
            if evaluated:
                for claim in sorted(head.claims, key=lambda c: c.claim_id):
                    key = head.module_id, claim.claim_id
                    self.sections['claims'].append({
                        'producer': producer, 'claim_id': claim.claim_id,
                        'text': claim.text, 'limitation': claim.limitation,
                        'citation_count': len(claim.citations),
                        'touching_kinds': [k for k in _PYTHON_KINDS if k in touching.get(key, ())]})
                    for ordinal, citation in enumerate(claim.citations, 1):
                        ref = cp5_integrity.citation_ref(claim.claim_id, ordinal)
                        self.sections['claim_citations'].append({
                            'producer': producer, 'claim_id': claim.claim_id, 'ref': ref,
                            'citation': {'source_id': citation.source_id,
                                         'source_sha256': citation.source_sha256,
                                         'locator': citation.locator},
                            'flagged': ref in self.checks.ref_marks.get(head.module_id, ())})
                for fact in sorted(head.facts, key=lambda f: (f.table_id, f.row_id, f.field, f.fact_id)):
                    self.sections['fact_index'].append({
                        'producer': producer, 'coordinate': dict(zip(_COORD_KEYS, _coordinate(fact), strict=True)),
                        'fact_sha256': fact.content_hash()})
                    key = head.module_id, fact.fact_id
                    if key in reasons:
                        self.sections['required_evidence'].append({
                            'producer': producer, 'fact': self.safe_fact(head.module_id, fact, catalog_citations=True),
                            'reasons': sorted(reasons[key]), 'claim_ids': sorted(claim_ids.get(key, ()))})
            for origin, texts in [('upstream_module', head.limitations), ('inherited', head.inherited_limitations)]:
                for ordinal, text in enumerate(texts):
                    self.sections['limitations'].append({
                        'producer': producer, 'origin': origin, 'ordinal': ordinal,
                        'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                        'label': 'Upstream restriction retained'})
        for ordinal, text in enumerate(scope.inherited):
            self.sections['limitations'].append({
                'producer': None, 'origin': 'inherited', 'ordinal': ordinal,
                'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'label': 'Upstream restriction retained'})
        # A single producer-qualified order also preserves duplicate citation ordinals.
        self.sections['fact_citations'].sort(key=lambda r: (
            cp5_integrity._rank(r['owner_fact']['producer_module_id']),
            r['owner_fact']['ref'], r['ordinal']))
        self.commitments = [{'section': s, 'count': len(self.sections[s]),
                             'sha256': _digest(self.sections[s])} for s in _SECTIONS]
        self.manifest_sha256 = _digest({
            'schema_version': 'cp5-scope-catalog/1', 'grant_sha256': self.grant_sha256,
            'scope_sha256': self.scope_sha256, 'sections': self.commitments})

    def ref(self, mid: str, kind: str, local: str) -> dict[str, str]:
        if kind == 'fact':
            valid = (mid, local) in self.facts
        elif kind == 'claim':
            valid = (mid, local) in self.claims
        elif kind == 'claim_citation':
            valid = local in cp5_integrity.upstream_refs(self.heads[mid]) and '#c' in local
        else:
            valid = False
        if not valid:
            raise _Refusal('internal_error')
        return {'producer_module_id': mid, 'producer_sha256': self.heads[mid].content_hash(),
                'kind': kind, 'ref': local}

    def safe_findings(self, findings: Any, *, final: bool = False,
                      submission: Any = None) -> list[dict[str, Any]]:
        records = []
        for ordinal, finding in enumerate(findings):
            if finding.kind not in (cp5_integrity.KINDS if final else _PYTHON_KINDS):
                raise _Refusal('internal_error')
            producers = []
            for mid in finding.modules:
                head = self.heads.get(mid)
                if head is not None:
                    producers.append(_producer_ref(head))
                else:
                    item = next((i for i in self.scope.inputs if i.input_id == mid), None)
                    if item is None or finding.kind != 'blocked_upstream':
                        raise _Refusal('internal_error')
                    producers.append({'module_id': mid, 'sha256': item.sha256, 'status': item.status})
            record: dict[str, Any] = {
                'finding_id': 'finding:' + _digest({'scope': self.scope_sha256,
                    'kind': finding.kind, 'ordinal': ordinal}),
                'ordinal': ordinal, 'code': finding.kind, 'producers': producers,
                'claim_refs': [], 'fact_refs': [], 'citation_refs': [],
                'identity_group_id': None, 'limited': None,
            }
            if final:
                record['origin'] = 'python' if finding.kind in _PYTHON_KINDS else 'analyst'
            if finding.kind == 'figure_identity':
                group = self.groups.get(finding.subject)
                if group is None or not group['differing']:
                    raise _Refusal('internal_error')
                record['identity_group_id'] = group['group_id']
                record['fact_refs'] = group['members']
            elif finding.kind in {'fact_citation', 'scale_unit'}:
                if len(finding.modules) != 1:
                    raise _Refusal('internal_error')
                mid = finding.modules[0]
                matches = [fid for owner, fid in self.facts
                           if owner == mid and finding.subject == 'fact ' + fid]
                if len(matches) != 1:
                    raise _Refusal('internal_error')
                record['fact_refs'] = [self.ref(mid, 'fact', matches[0])]
            elif finding.kind in {'claim_citation', 'claim_figure', 'unsettled_fact',
                                  'unsupported_claim', 'partly_supported_claim'}:
                if len(finding.modules) != 1:
                    raise _Refusal('internal_error')
                mid = finding.modules[0]
                matches = [cid for owner, cid in self.claims
                           if owner == mid and finding.subject == 'claim ' + cid]
                if len(matches) != 1:
                    raise _Refusal('internal_error')
                cid = matches[0]
                record['claim_refs'] = [self.ref(mid, 'claim', cid)]
                if finding.kind == 'claim_citation':
                    claim = self.claims[mid, cid]
                    record['citation_refs'] = [self.ref(mid, 'claim_citation',
                        cp5_integrity.citation_ref(cid, n))
                        for n, citation in enumerate(claim.citations, 1)
                        if citation_issues((citation,), self.scope.pack.sources)]
                    if not record['citation_refs']:
                        raise _Refusal('internal_error')
                elif finding.kind == 'unsettled_fact':
                    items = [u for u in self.checks.unsettled if (u.module_id, u.claim_id) == (mid, cid)]
                    if len(items) != 1:
                        raise _Refusal('internal_error')
                    record['fact_refs'] = [self.ref(mid, 'fact', fid) for fid in items[0].fact_ids]
                    record['limited'] = items[0].limited
                else:
                    record['fact_refs'] = [self.ref(mid, 'fact', fid)
                                           for fid in sorted(self.named.get((mid, cid), ()))]
            elif finding.kind == 'contradiction':
                if submission is None:
                    raise _Refusal('internal_error')
                # The core de-duplicates equal findings (cp5_integrity._ordered), so any number of
                # submitted contradictions can back one finding; their pairs are equal by subject.
                matched = [c for c in submission.contradictions
                           if cp5_integrity._contradiction_finding(c) == finding]
                if not matched:
                    raise _Refusal('internal_error')
                pairs = sorted({(r.producer_module, r.claim_ref) for r in matched[0].claim_refs},
                               key=lambda pair: (cp5_integrity._rank(pair[0]), pair[1]))
                record['claim_refs'] = [self.ref(m, 'claim', cid) for m, cid in pairs]
            elif finding.kind == 'blocked_upstream':
                if len(finding.modules) != 1 or finding.modules[0] not in self.scope.blocked:
                    raise _Refusal('internal_error')
            elif finding.kind == 'empty_evaluated_set':
                if self.scope.evaluated or finding.modules:
                    raise _Refusal('internal_error')
            records.append(record)
        return records

    def _citation_set(self, mid: str, fact: Fact) -> dict[str, Any]:
        key = mid, fact.fact_id
        if key not in self.citation_sets:
            handles = _handles(fact)
            digest = _digest(handles)
            handle = 'fact-citations:' + _digest({'producer_sha256': self.heads[mid].content_hash(),
                'fact_id': fact.fact_id, 'fact_sha256': fact.content_hash(), 'handles_sha256': digest})
            self.citation_sets[key] = {'projection': 'fact_citation_catalog/1',
                                      'handle': handle, 'count': len(handles), 'sha256': digest}
            self.sections['fact_citations'].extend({
                'owner_fact': self.ref(mid, 'fact', fact.fact_id), 'ordinal': n, 'citation': h}
                for n, h in enumerate(handles))
        return self.citation_sets[key]

    def safe_fact(self, mid: str, fact: Fact, *, catalog_citations: bool = False,
                  fields: list[str] | None = None) -> dict[str, Any]:
        selected = sorted(_KEYS) if fields is None else fields
        result = _project_fields(fact, selected)
        result['fact_sha256'] = fact.content_hash()
        for attribute in ('text', 'basis'):
            if attribute not in result:
                continue
            commitment = self.protected.get((mid, fact.fact_id, attribute))
            if commitment is not None:
                result[attribute] = commitment
                continue
            raw = result[attribute]
            if isinstance(raw, str) and raw.lstrip().startswith(('{', '[')):
                try:
                    parsed = _strict_json(raw)
                except (ValueError, RecursionError):
                    # Not JSON: ordinary analyst prose may begin with a reference chip or bracket,
                    # and the contract forbids generic redaction of permitted prose.
                    pass
                else:
                    if isinstance(parsed, (dict, list)):
                        raise _Refusal('not_permitted')
        if 'citation_handles' in result and (catalog_citations or (mid, fact.fact_id) in self.citation_sets):
            result['citation_handles'] = self._citation_set(mid, fact)
        return result

    def _lineage_catalogs(self, reasons: dict[tuple[str, str], set[str]]) -> None:
        """Validate the narrow frozen B1 structure; never import its workflow."""
        mid = 'CP-1B'
        head = self.heads.get(mid)
        if head is None or head.status == 'blocked':
            return
        bundles = [f for f in head.facts if (f.fact_id, f.table_id, f.row_id, f.field) == (
            'cp1b:T1B.3:evidence.inputs:assessment', 'T1B.3', 'evidence.inputs', 'assessment')]
        if not bundles:
            return
        if len(bundles) != 1 or 'CP-1' not in self.heads or len(head.facts) != 44:
            raise _Refusal('not_permitted')
        fact = bundles[0]
        try:
            if fact.text is None:
                raise _Refusal('not_permitted')
            try:
                bundle = _strict_json(fact.text)
            except (ValueError, RecursionError):
                raise _Refusal('not_permitted') from None
            _object(bundle, {'producer_module_id', 'producer_sha256', 'prior_period_id',
                'current_period_id', 'prior_basis_id', 'current_basis_id', 'operands'})
            if _canonical(bundle).decode() != fact.text:
                raise _Refusal('not_permitted')
            source = self.heads['CP-1']
            if (bundle['producer_module_id'] != 'CP-1'
                    or bundle['producer_sha256'] != source.content_hash()):
                raise _Refusal('not_permitted')
            for name in ('prior_period_id', 'current_period_id', 'current_basis_id'):
                _identifier(bundle[name])
            if bundle['prior_basis_id'] is not None:
                _identifier(bundle['prior_basis_id'])
            operands = _array(bundle['operands'])
            if len(operands) != 12:
                raise _Refusal('not_permitted')
            expected = self._lineage_expectation(source, bundle)
            raw_hash = hashlib.sha256(fact.text.encode()).hexdigest()
            bid = 'lineage-bundle:' + _digest({'producer_sha256': head.content_hash(),
                'fact_id': fact.fact_id, 'raw_sha256': raw_hash})
            self.protected[mid, fact.fact_id, 'text'] = self._payload('cp1b_evidence_bundle', fact.text, bid)
            lineage_by_raw: dict[str, str] = {}
            for ordinal, (measure, lineage) in enumerate(zip(_LINEAGE_MEASURES, operands, strict=True)):
                _object(lineage, {'measure_id', 'prior', 'current', 'companions'})
                if lineage['measure_id'] != measure:
                    raise _Refusal('not_permitted')
                raw = _canonical(lineage).decode()
                lh = hashlib.sha256(raw.encode()).hexdigest()
                lid = 'lineage:' + _digest({'producer_sha256': head.content_hash(),
                                           'measure_id': measure, 'raw_sha256': lh})
                lineage_by_raw[raw] = lid
                derived = expected[measure]
                companion_refs = _array(lineage['companions'])
                if companion_refs != [self._fact_reference(f) for f in derived.companions]:
                    raise _Refusal('not_permitted')
                companion_records = []
                for number, ref in enumerate(companion_refs):
                    self._lineage_fact(ref)
                    reasons.setdefault(('CP-1', ref['fact_id']), set()).add('lineage_companion')
                    companion_records.append({'lineage_id': lid, 'ordinal': number, 'fact': ref})
                self.sections['lineage_companions'].extend(companion_records)
                opids: dict[str, str | None] = {'prior': None, 'current': None}
                for role in ('prior', 'current'):
                    operand = lineage[role]
                    primary = derived.primary[role]
                    if primary is None:
                        # Absence was proven against the current CP1 in _lineage_expectation.
                        if operand is not None:
                            raise _Refusal('not_permitted')
                        continue
                    _object(operand, {'fact', 'period_id', 'basis_id', 'source_period',
                                      'source_basis', 'fact_sha256', 'citation_handles'})
                    sf = self._lineage_fact(operand['fact'])
                    period_id, basis_id = derived.identities[role]
                    if (operand['fact'] != self._fact_reference(primary) or sf != primary
                            or operand['period_id'] != period_id or operand['basis_id'] != basis_id
                            or type(operand['source_period']) is not str
                            or type(operand['source_basis']) is not str
                            or sf.period != operand['source_period'] or sf.basis != operand['source_basis']
                            or sf.content_hash() != operand['fact_sha256']
                            or _handles(sf) != operand['citation_handles']):
                        raise _Refusal('not_permitted')
                    reasons.setdefault(('CP-1', sf.fact_id), set()).add('lineage_primary')
                    opid = 'lineage-operand:' + _digest({'lineage_id': lid, 'role': role})
                    opids[role] = opid
                    citations = [{'lineage_id': lid, 'operand_id': opid, 'ordinal': n, 'citation': h}
                                 for n, h in enumerate(_handles(sf))]
                    self.sections['lineage_citations'].extend(citations)
                    self.sections['lineage_operands'].append({
                        'operand_id': opid, 'lineage_id': lid, 'role': role, 'fact': operand['fact'],
                        'period_id': operand['period_id'], 'basis_id': operand['basis_id'],
                        'source_period': sf.period,
                        'source_basis_sha256': hashlib.sha256(operand['source_basis'].encode()).hexdigest(),
                        'source_basis_bytes': len(operand['source_basis'].encode()),
                        'fact_sha256': sf.content_hash(), 'citation_count': len(citations),
                        'citations_sha256': _digest(citations)})
                self.sections['lineage_headers'].append({
                    'lineage_id': lid, 'bundle_id': bid, 'ordinal': ordinal, 'measure_id': measure,
                    'raw_sha256': lh, 'raw_bytes': len(raw.encode()),
                    'prior_operand_id': opids['prior'], 'current_operand_id': opids['current'],
                    'companion_count': len(companion_records),
                    'companions_sha256': _digest(companion_records)})
            for owner_fact in head.facts:
                if owner_fact.basis is not None and owner_fact.basis.lstrip().startswith('{'):
                    if owner_fact.basis not in lineage_by_raw:
                        raise _Refusal('not_permitted')
                    self.protected[mid, owner_fact.fact_id, 'basis'] = self._payload(
                        'cp1b_operand_lineage', owner_fact.basis, lineage_by_raw[owner_fact.basis])
                self.sections['lineage_owner_facts'].append({
                    'owner': _producer_ref(head),
                    'coordinate': dict(zip(_COORD_KEYS, _coordinate(owner_fact), strict=True)),
                    'fact_sha256': owner_fact.content_hash(),
                    'citation_set': self._citation_set(mid, owner_fact),
                    'basis_commitment': self.protected.get((mid, owner_fact.fact_id, 'basis')),
                    'text_commitment': self.protected.get((mid, owner_fact.fact_id, 'text'))})
            headers = [h['lineage_id'] for h in self.sections['lineage_headers']]
            self.sections['lineage_bundles'].append({
                'bundle_id': bid, 'owner': _producer_ref(head),
                'owner_fact': self.ref(mid, 'fact', fact.fact_id), 'raw_sha256': raw_hash,
                'raw_bytes': len(fact.text.encode()), 'source_producer': _producer_ref(source),
                **{k: bundle[k] for k in ('prior_period_id', 'current_period_id', 'prior_basis_id', 'current_basis_id')},
                'lineage_count': 12, 'lineages_sha256': _digest(headers),
                'owner_fact_count': len(head.facts),
                'owner_facts_sha256': _digest(self.sections['lineage_owner_facts'])})
        except _Refusal as error:
            # Only explicit validation refusals describe the bundle; an internal error is not one.
            if str(error) == 'internal_error':
                raise
            raise _Refusal('not_permitted') from None
        except Exception:  # noqa: BLE001 - fail closed: unexpected errors stay internal_error
            raise _Refusal('internal_error') from None

    def _fact_reference(self, fact: Fact) -> dict[str, str]:
        return {'producer_module_id': 'CP-1',
                'producer_sha256': self.heads['CP-1'].content_hash(),
                **dict(zip(_COORD_KEYS, _coordinate(fact), strict=True))}

    def _lineage_expectation(self, source: Module, bundle: dict[str, Any]) -> dict[str, _Derived]:
        """Re-derive every lineage from the current full CP1, never from the bundle's claims.

        Follows the frozen reference derivation (cp5-fixture-reference-contract.md): T4.14 period
        rows keyed by period_id text, T4.10 metric rows keyed by field_1 text, the primary fact
        of a role being the metric-row fact named by that period's model-basis id.
        Partial absence (a period row without its measure fact, an incomplete period row, a
        basis fact without its period row) is an open semantic question and refuses.
        """
        period_rows: dict[str, dict[str, Fact]] = {}
        metric_rows: dict[str, dict[str, Fact]] = {}
        for fact in source.facts:
            if fact.table_id == 'T4.14':
                period_rows.setdefault(fact.row_id, {})[fact.field] = fact
            elif fact.table_id == 'T4.10':
                metric_rows.setdefault(fact.row_id, {})[fact.field] = fact
        periods: dict[str, dict[str, Fact]] = {}
        for row in period_rows.values():
            identity = row.get('period_id')
            if identity is not None and identity.text is not None:
                if identity.text in periods:
                    raise _Refusal('not_permitted')
                periods[identity.text] = row
        metrics: dict[str, dict[str, Fact]] = {}
        for row in metric_rows.values():
            name = row.get('field_1')
            if name is not None and name.text is not None:
                if name.text in metrics:
                    raise _Refusal('not_permitted')
                metrics[name.text] = row
        prior_id, current_id = bundle['prior_period_id'], bundle['current_period_id']
        if prior_id == current_id:
            raise _Refusal('not_permitted')

        def basis(column: str) -> str:
            raw = ''.join(f'{len(part)}:{part}' for part in ('historical', column))
            return 'model-basis:' + hashlib.sha256(raw.encode()).hexdigest()

        def derive(pid: str) -> tuple[dict[str, Fact], str]:
            row = periods.get(pid)
            if row is None or not set(_PERIOD_FIELDS) <= row.keys():
                raise _Refusal('not_permitted')
            kind = row['period_type'].text
            if kind not in {'QUARTER', 'FY'}:
                raise _Refusal('not_permitted')
            return row, basis(('Q:' if kind == 'QUARTER' else 'FY:') + pid)

        current_row, current_basis = derive(current_id)
        if bundle['current_basis_id'] != current_basis:
            raise _Refusal('not_permitted')
        prior_row: dict[str, Fact] | None = None
        prior_basis: str | None = None
        if prior_id in periods:
            present_row, present_basis = derive(prior_id)
            if bundle['prior_basis_id'] != present_basis:
                raise _Refusal('not_permitted')
            # A1 (earnings.py _duration_period/compatibility): same kind, equal duration, current after prior.
            try:
                p_start, p_end = (date.fromisoformat(present_row[k].text or '') for k in ('start_date', 'end_date'))
                c_start, c_end = (date.fromisoformat(current_row[k].text or '') for k in ('start_date', 'end_date'))
            except ValueError:
                raise _Refusal('not_permitted') from None
            if (present_row['period_type'].text != current_row['period_type'].text
                    or p_end - p_start != c_end - c_start or not c_start > p_end):
                raise _Refusal('not_permitted')
            prior_row, prior_basis = present_row, present_basis
        else:
            # Genuine absence: no T4.14 row and no T4.10 fact at either possible basis field.
            unseen = {basis('Q:' + prior_id), basis('FY:' + prior_id)}
            if bundle['prior_basis_id'] is not None or any(
                    f.field in unseen for row in metric_rows.values() for f in row.values()):
                raise _Refusal('not_permitted')
        derived: dict[str, _Derived] = {}
        for measure in _LINEAGE_MEASURES:
            metric = metrics.get(measure)
            current = None if metric is None else metric.get(current_basis)
            prior = None if metric is None or prior_basis is None else metric.get(prior_basis)
            if metric is None or current is None or (prior_basis is not None and prior is None):
                raise _Refusal('not_permitted')
            companions = [metric['field_1'], *(
                period[name] for period in (prior_row, current_row) if period is not None
                for name in _PERIOD_FIELDS)]
            derived[measure] = _Derived(
                {'prior': prior, 'current': current}, companions,
                {'prior': (prior_id, prior_basis), 'current': (current_id, current_basis)})
        return derived

    def _lineage_fact(self, ref: Any) -> Fact:
        _object(ref, {'producer_module_id', 'producer_sha256', *_COORD_KEYS})
        for key in _COORD_KEYS:
            _identifier(ref[key])
        sf = self.facts.get(('CP-1', ref['fact_id']))
        if (sf is None or ref['producer_module_id'] != 'CP-1'
                or ref['producer_sha256'] != self.heads['CP-1'].content_hash()
                or tuple(ref[k] for k in _COORD_KEYS) != _coordinate(sf)):
            raise _Refusal('not_permitted')
        return sf

    @staticmethod
    def _payload(kind: str, raw: str, handle: str) -> dict[str, Any]:
        return {'schema_version': 'cp5-protected-payload/1', 'kind': kind,
                'raw_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                'raw_bytes': len(raw.encode()), 'handle': handle,
                'projection': 'bounded_lineage_catalog/1'}

    def header(self) -> dict[str, Any]:
        producers = self.sections['producers']
        return {'grant_sha256': self.grant_sha256, 'scope_sha256': self.scope_sha256,
                'manifest_sha256': self.manifest_sha256,
                'evaluated_count': sum(p['role'] == 'evaluated' for p in producers),
                'blocked_count': sum(p['role'] == 'blocked' for p in producers),
                'fact_count': len(self.facts), 'claim_count': len(self.claims),
                'claim_citation_count': len(self.sections['claim_citations'])}


class _IntegrityTools(UpstreamTools):
    """CP5-v2 session with distinct catalogs, issued cursors and no raw source path."""

    def __init__(self, store: Execution, ticket_id: str, step_id: str,
                 *, grants: Mapping[str, Any]) -> None:
        try:
            try:
                snapshot, attempt, pack, modules = _context(store, ticket_id, step_id)
                if attempt.module_id != 'CP-5' or pack.run != snapshot.run:
                    raise _Refusal('not_permitted')
                if (attempt.interruption is not None or attempt.issues or attempt.result_sha256 is not None
                        or [a for a in snapshot.attempts if a.module_id == 'CP-5'][-1] != attempt):
                    raise _Refusal('stale_binding')
                self._store, self._attempt, self._step_id = store, attempt, step_id
                self._snapshot_sha256 = snapshot.content_hash()
                self._binding = {
                    'run_id': snapshot.run.run_id, 'issuer_id': snapshot.run.issuer_id,
                    'as_of': snapshot.run.as_of.isoformat(), 'method_version': snapshot.run.method_version,
                    'pack_sha256': pack.content_hash(), 'snapshot_sha256': self._snapshot_sha256,
                    'module_id': 'CP-5', 'step_id': step_id, 'ticket_id': ticket_id,
                    'attempt': attempt.number, 'inputs': [i.model_dump(mode='json') for i in attempt.inputs],
                }
                scope = cp5_integrity.review_scope(store, attempt)
                if {i.input_id: h for i, h in scope.heads} != {
                    mid: h for mid, h in modules.items() if mid not in cp5_integrity.NOT_EVALUATED
                }:
                    raise _Refusal('identity_mismatch')
            except _Refusal:
                raise
            except (ValueError, OSError, KeyError, TypeError):
                # Tampered/missing store bytes or an unresolvable head: lease L102 identity_mismatch.
                raise _Refusal('identity_mismatch') from None
            self._catalog = _IntegrityCatalog(scope, self._binding, grants)
            self._nonce = uuid4().hex
            self._session_id = str(uuid4())
            self._integrity_cursors: dict[str, tuple[str, int]] = {}
            self._sequence = 0
            self._lock, self._receipt_lock = Lock(), Lock()
            self._receipts: list[str] = []
            self._current()
            if len(_canonical(self._integrity_manifest())) > 8192:
                raise _Refusal('bad_arguments')
        except _Refusal:
            raise
        except Exception:  # noqa: BLE001 - fail closed with a sanitized public category
            raise ValueError('internal_error') from None

    def _current(self) -> tuple[PreparedPack, dict[str, Module]]:
        try:
            if self._store.read().content_hash() != self._snapshot_sha256:
                raise _Refusal('stale_binding')
            snapshot, attempt, pack, modules = _context(self._store, self._attempt.ticket_id, self._step_id)
            if snapshot.content_hash() != self._snapshot_sha256 or attempt != self._attempt:
                raise _Refusal('stale_binding')
            if pack.run != snapshot.run or pack.content_hash() != self._binding['pack_sha256']:
                raise _Refusal('identity_mismatch')
            if self._store.read().content_hash() != self._snapshot_sha256:
                raise _Refusal('stale_binding')
            return pack, modules
        except _Refusal:
            raise
        except (OSError, ValueError, TypeError, KeyError):
            raise _Refusal('identity_mismatch') from None

    @property
    def access_manifest(self) -> dict[str, Any]:
        raise _Refusal('not_permitted')

    def _integrity_manifest(self) -> dict[str, Any]:
        return {'schema_version': 'cp5-integrity-manifest/1', 'binding': self._binding,
                'session_id': self._session_id, **self._catalog.header(),
                'producer_count': len(self._catalog.heads), 'sections': self._catalog.commitments,
                'limits': _INTEGRITY_LIMITS}

    @property
    def integrity_manifest(self) -> dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            raise _Refusal('not_permitted')
        try:
            self._current()
            result: dict[str, Any] = json.loads(_canonical(self._integrity_manifest()))
            self._current()
            return result
        except _Refusal:
            raise
        except Exception:  # noqa: BLE001 - fail closed: sanitized public category
            raise ValueError('internal_error') from None
        finally:
            self._lock.release()

    def _scope_page(self, args: dict[str, Any]) -> tuple[dict[str, Any], tuple[str, tuple[str, int]] | None]:
        _object(args, {'scope_sha256', 'section', 'cursor', 'limit'})
        self._scope_identity(args['scope_sha256'])
        section, cursor, limit = args['section'], args['cursor'], args['limit']
        if type(section) is not str or section not in _SECTIONS:
            raise _Refusal('bad_arguments')
        if type(limit) is not int or not 1 <= limit <= 20:
            raise _Refusal('bad_arguments')
        offset = 0
        if cursor is not None:
            if type(cursor) is not str or re.fullmatch('integrity-cursor:[0-9a-f]{64}', cursor) is None:
                raise _Refusal('bad_arguments')
            issued = self._integrity_cursors.get(cursor)
            if issued is None or issued[0] != section:
                raise _Refusal('stale_binding')
            offset = issued[1]
        entries = self._catalog.sections[section]
        total = len(entries)
        header = {'scope_sha256': self._catalog.scope_sha256,
                  'grant_sha256': self._catalog.grant_sha256,
                  'manifest_sha256': self._catalog.manifest_sha256,
                  'section': section, 'total': total, 'offset': offset}
        if total == 0:
            body = {**header, 'entries': [], 'next_cursor': None, 'complete': True}
            if len(_canonical(body)) > 8192:
                raise _Refusal('bad_arguments')
            return body, None
        best = None
        for end in range(offset + 1, min(offset + limit, total) + 1):
            token = None if end == total else 'integrity-cursor:' + _digest({
                'nonce': self._nonce, 'session_id': self._session_id, 'binding': self._binding,
                'scope_sha256': self._catalog.scope_sha256, 'grant_sha256': self._catalog.grant_sha256,
                'manifest_sha256': self._catalog.manifest_sha256, 'section': section, 'offset': end})
            body = {**header, 'entries': entries[offset:end], 'next_cursor': token, 'complete': end == total}
            if len(_canonical(body)) <= 8192:
                best = (body, None if token is None else (token, (section, end)))
        if best is None:
            raise _Refusal('bad_arguments')
        return best

    def _scope_identity(self, digest: Any) -> None:
        if _hash_string(digest) != self._catalog.scope_sha256:
            raise _Refusal('identity_mismatch')

    def _integrity_producer(self, args: dict[str, Any]) -> Module:
        mid = _identifier(args['producer_module_id'])
        digest = _hash_string(args['producer_sha256'])
        head = self._catalog.heads.get(mid)
        if head is None or head.status == 'blocked':
            raise _Refusal('not_permitted')
        if digest != head.content_hash():
            raise _Refusal('identity_mismatch')
        return head

    def _integrity_lookup(self, args: dict[str, Any]) -> dict[str, Any]:
        _object(args, _LOOKUP_KEYS)
        head = self._integrity_producer(args)
        rows, fields = _strings(args['row_ids'], 20), _strings(args['fields'], 16)
        table = _identifier(args['table_id'])
        for row in rows:
            _identifier(row)
        if not _IDENTITY_KEYS <= set(fields):
            raise _Refusal('bad_arguments')
        if not set(fields) <= _KEYS:
            raise _Refusal('not_permitted')
        available: dict[str, list[Fact]] = {}
        for fact in sorted(head.facts, key=lambda f: (f.table_id, f.row_id, f.field, f.fact_id)):
            if fact.table_id == table:
                available.setdefault(fact.row_id, []).append(fact)
        if not set(rows) <= available.keys():
            raise _Refusal('not_permitted')
        return {'producer': _producer_ref(head), 'projection': 'safe_scope_fact_projection',
                'scope_sha256': self._catalog.scope_sha256, 'grant_sha256': self._catalog.grant_sha256,
                'manifest_sha256': self._catalog.manifest_sha256, 'table_id': table,
                'rows': [{'row_id': row, 'facts': [self._catalog.safe_fact(head.module_id, f, fields=fields)
                          for f in available[row]]} for row in rows]}

    def _integrity_verify(self, args: dict[str, Any], pack: PreparedPack) -> dict[str, Any]:
        _object(args, _VERIFY_KEYS)
        kind = args['kind']
        # The kind is checked first, as in v1: a malformed kind is bad_arguments and the
        # unavailable 'integrity' kind is not_permitted whatever the producer hash says.
        if type(kind) is not str or kind not in {'citations', 'integrity'}:
            raise _Refusal('bad_arguments')
        if kind != 'citations':
            raise _Refusal('not_permitted')
        head = self._integrity_producer(args)
        ids = _strings(args['fact_ids'], 20)
        facts = {f.fact_id: f for f in head.facts}
        if not set(ids) <= facts.keys():
            raise _Refusal('not_permitted')
        issues = [{'code': 'fact_citation', 'fact_ids': [fid]} for fid in ids
                  for _ in citation_issues(facts[fid].citations, pack.sources)]
        return {'producer': _producer_ref(head), 'scope_sha256': self._catalog.scope_sha256,
                'grant_sha256': self._catalog.grant_sha256, 'manifest_sha256': self._catalog.manifest_sha256,
                'kind': 'citations', 'verdict': 'invalid' if issues else 'valid',
                'issue_count': len(issues), 'issues': issues}

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            supplied = _strict_json(_canonical(arguments).decode())
        except (ValueError, TypeError, RecursionError):
            raise ValueError('bad_arguments') from None
        acquired = self._lock.acquire(blocking=False)
        try:
            try:
                with self._receipt_lock:
                    self._sequence += 1
                    sequence = self._sequence
                receipt = {'schema_version': 'tool-receipt/1', 'call_id': str(uuid4()),
                           'sequence': sequence, 'binding': json.loads(_canonical(self._binding)),
                           'tool': tool_name, 'arguments': supplied, 'status': 'refused', 'body': None,
                           'error_code': None, 'source_evidence': {
                               'read': [], 'extracted': [], 'surfaced': [], 'searched': []}}
            except Exception:  # noqa: BLE001 - fail closed: sanitized public category
                raise ValueError('internal_error') from None
            staged = None
            try:
                if not acquired:
                    raise _Refusal('not_permitted')
                if type(tool_name) is not str or tool_name not in {
                    'lookup_upstream', 'verify_upstream', 'read_integrity_scope', 'verify_integrity_scope'}:
                    raise _Refusal('not_permitted')
                if type(supplied) is not dict:
                    raise _Refusal('bad_arguments')
                pack, _ = self._current()
                if tool_name == 'read_integrity_scope':
                    body, staged = self._scope_page(supplied)
                elif tool_name == 'lookup_upstream':
                    body = self._integrity_lookup(supplied)
                elif tool_name == 'verify_upstream':
                    body = self._integrity_verify(supplied, pack)
                else:
                    _object(supplied, {'scope_sha256'})
                    self._scope_identity(supplied['scope_sha256'])
                    # Run the existing checks again on the complete current authentic scope.
                    try:
                        reread = cp5_integrity.review_scope(self._store, self._attempt)
                    except (ValueError, OSError):
                        # Fail closed: unreadable or tampered store bytes are an identity failure.
                        raise _Refusal('identity_mismatch') from None
                    if reread.issues or {h.module_id: h for _, h in reread.heads} != self._catalog.heads:
                        raise _Refusal('identity_mismatch')
                    checks = cp5_integrity.python_checks(reread)
                    if self._catalog.safe_findings(checks.findings) != self._catalog.sections['findings']:
                        raise _Refusal('identity_mismatch')
                    counts = {k: sum(f.kind == k for f in checks.findings) for k in _PYTHON_KINDS}
                    body = {**self._catalog.header(),
                            'mechanical_verdict': 'findings' if checks.findings else 'clean',
                            'category_counts': counts,
                            'findings_sha256': _digest(self._catalog.sections['findings'])}
                if len(_canonical(body)) > 8192:
                    raise _Refusal('bad_arguments')
                self._current()
                receipt.update(status='ok', body=body)
            except _Refusal as error:
                receipt.update(status='refused', error_code=str(error), body=None)
            except Exception:  # noqa: BLE001 - unexpected errors become an internal_error receipt
                receipt.update(status='error', error_code='internal_error', body=None)
            except BaseException:
                receipt.update(status='error', error_code='internal_error', body=None)
                self._retain_projection(receipt)
                raise
            self._retain_projection(receipt)
            if receipt['status'] == 'ok' and staged is not None:
                token, position = staged
                self._integrity_cursors[token] = position
            # Hand back a fresh decoded copy so no caller can alias catalog or retained state.
            detached: dict[str, Any] = json.loads(json.dumps(
                receipt, ensure_ascii=False, allow_nan=False, separators=(',', ':')))
            return detached
        finally:
            if acquired:
                self._lock.release()
