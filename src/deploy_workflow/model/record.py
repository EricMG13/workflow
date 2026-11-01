"""``model-call/1`` records, the redacted raw archive and the invocation digest audit.

Layout, under a run directory: ``calls.jsonl`` (one redacted record per line), ``raw/<digest>-<n>.json``
(the redacted reply body). The digest preimage is retained beside the Execution's other audit
kinds at ``<Execution dir>/owner-run-audit/invocations/<digest>``.

Redaction happens before a record is built (``CallRecord.build`` / ``refused`` pass error text
through ``Redactor.text`` / ``Redactor.exception``) and again over the whole record when it is
written. This module never reads ``os.environ``: the caller's ``Redactor`` carries the key values.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import fields
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import ConfigDict, Field, field_serializer, model_validator

from deploy_vii.contracts import Contract, Hash
from deploy_workflow.model.pricing import CostStatus, money_text, refusal_values
from deploy_workflow.model.providers import ErrorKind, ProviderError, parse
from deploy_workflow.model.redact import KEY_PATTERN, Redactor
from deploy_workflow.model.turn import (
    TurnError,
    Usage,
    dump_json,
    load_json,
    turn_to_json,
)

AUDIT = "owner-run-audit"  # owner_workflow.AUDIT
INVOCATIONS = "invocations"
METHOD_VERSION = "deploy-v-r14"
_DIGEST = re.compile(r"[0-9a-f]{64}")
_PREIMAGE_KEYS = frozenset(
    {
        "run_id",
        "module_id",
        "step_id",
        "attempt",
        "upstream_hashes",
        "prompt_sha256",
        "method_version",
    }
)
_KIND_NAME = {
    ErrorKind.NOT_SENT: "not_sent",
    ErrorKind.SENT_CHARGE_KNOWN: "sent_known",
    ErrorKind.SENT_CHARGE_USAGE: "sent_usage",
    ErrorKind.SENT_CHARGE_UNKNOWN: "sent_unknown",
}


class RawExists(FileExistsError):
    """A raw body was already archived for this (digest, call_index); never overwritten."""


class RawMissing(LookupError):
    """A record has no archived raw body to rebuild its recording from."""


class AuditCorrupt(ValueError):
    """Bytes already at an audit path differ from the bytes that belong there."""


class ToolCallRecord(Contract):
    model_config = ConfigDict(hide_input_in_errors=True)

    name: str
    arguments_sha256: Hash
    result_bytes: int | None = Field(ge=0)
    refusal_code: str | None


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, list | tuple):
        return [s for item in value for s in _strings(item)]
    return []


class CallRecord(Contract):
    # F4: contracts.Contract does not hide the input, so a rejected value would be echoed.
    model_config = ConfigDict(hide_input_in_errors=True)

    schema_version: Literal["model-call/1"]
    run_id: str
    case_id: str
    pathway: str
    module_id: str
    step_id: str
    attempt: Literal[0, 1]
    call_index: int = Field(ge=0)
    config_id: str
    provider: str
    requested_model: str
    reported_model: str | None
    requested_effort: str
    invocation_digest: Hash
    request_id: str | None
    http_status: int | None
    started_at: datetime
    first_byte_at: datetime | None
    finished_at: datetime | None
    input_tokens: int | None = Field(ge=0)
    cached_read_tokens: int | None = Field(ge=0)
    cache_write_tokens: int | None = Field(ge=0)  # the sum; the 5m/1h split is not recorded
    output_tokens: int | None = Field(ge=0)
    reasoning_tokens: int | None = Field(ge=0)
    reserved_usd: Decimal
    settled_usd: Decimal | None
    cost_status: CostStatus
    tool_calls: tuple[ToolCallRecord, ...]
    submit_sha256: Hash | None
    error_class: str | None
    error: str | None

    @field_serializer("reserved_usd", "settled_usd")
    def _money(self, value: Decimal | None) -> str | None:
        return None if value is None else money_text(value)

    @model_validator(mode="after")
    def _checked(self) -> CallRecord:
        if (self.cost_status == "unknown") != (self.settled_usd is None):
            raise ValueError("settled_usd is None exactly when cost_status is unknown")
        for text in _strings(self.model_dump(mode="json")):
            if KEY_PATTERN.search(text):
                raise ValueError("a record field holds key material")  # never the value
        return self

    @classmethod
    def build(cls, redactor: Redactor, **values: Any) -> CallRecord:
        """Construct after redacting ``error`` (a string, or an exception formatted with its chain)."""
        error = values.get("error")
        if isinstance(error, BaseException):
            values["error"] = redactor.exception(error)
        elif isinstance(error, str):
            values["error"] = redactor.text(error)
        return cls(**values)

    @classmethod
    def refused(
        cls, redactor: Redactor, *, error_class: str, error: str | BaseException, **values: Any
    ) -> CallRecord:
        """A call refused before any send: reserved and settled 0, computed, no tokens."""
        reserved, settled, status = refusal_values()
        base: dict[str, Any] = {
            "schema_version": "model-call/1",
            "reported_model": None,
            "request_id": None,
            "http_status": None,
            "first_byte_at": None,
            "finished_at": None,
            "tool_calls": (),
            "submit_sha256": None,
        }
        base.update(values)
        base.update(
            reserved_usd=reserved,
            settled_usd=settled,
            cost_status=status,
            input_tokens=None,
            cached_read_tokens=None,
            cache_write_tokens=None,
            output_tokens=None,
            reasoning_tokens=None,
            error_class=error_class,
            error=error,
        )
        return cls.build(redactor, **base)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view) :]


class CallLog:
    def __init__(self, run_dir: Path, redactor: Redactor) -> None:
        self._dir = Path(run_dir)
        self._redactor = redactor
        self._calls = self._dir / "calls.jsonl"
        self._raw = self._dir / "raw"

    def append(self, record: CallRecord) -> None:
        """Redact the record JSON, then write one fsynced line under an exclusive flock."""
        clean = self._redactor.json_value(record.model_dump(mode="json"))
        data = (json.dumps(clean) + "\n").encode()
        self._dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._calls, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            _write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)  # closing releases the lock

    def records(self) -> list[dict[str, Any]]:
        """Every line of ``calls.jsonl`` as written. A damaged line raises; none is skipped."""
        if not self._calls.exists():
            return []
        fd = os.open(self._calls, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            text = os.read(fd, os.fstat(fd).st_size).decode()
        finally:
            os.close(fd)
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def next_call_index(self, module_id: str, step_id: str, attempt: int) -> int:
        taken = [
            r["call_index"]
            for r in self.records()
            if (r["module_id"], r["step_id"], r["attempt"]) == (module_id, step_id, attempt)
        ]
        return max(taken, default=-1) + 1

    def write_raw(self, digest: str, call_index: int, body: bytes) -> Path:
        """Archive the redacted body at ``raw/<digest>-<call_index>.json``, create-once."""
        if not _DIGEST.fullmatch(digest):
            raise ValueError("digest must be 64 lowercase hex characters")
        if isinstance(call_index, bool) or not isinstance(call_index, int) or call_index < 0:
            raise ValueError("call_index must be a non-negative integer")
        text = body.decode("utf-8", errors="replace")
        try:
            stored = dump_json(self._redactor.json_value(load_json(text)))
        except TurnError:  # not JSON (SSE, plain text): keep the decoded text as a JSON string
            stored = json.dumps(self._redactor.text(text))
        self._raw.mkdir(parents=True, exist_ok=True)
        path = self._raw / f"{digest}-{call_index}.json"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise RawExists(path.name) from None
        try:
            _write_all(fd, stored.encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_dir(self._raw)
        return path


# ---------------------------------------------------------------- invocation digest


def invocation_preimage(
    *,
    run_id: str,
    module_id: str,
    step_id: str,
    attempt: int,
    upstream_hashes: list[str] | tuple[str, ...],
    prompt_sha256: str,
    method_version: str = METHOD_VERSION,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "module_id": module_id,
        "step_id": step_id,
        "attempt": attempt,
        "upstream_hashes": sorted(upstream_hashes),
        "prompt_sha256": prompt_sha256,
        "method_version": method_version,
    }


def _canonical(preimage: Mapping[str, Any]) -> bytes:
    if set(preimage) != _PREIMAGE_KEYS:
        raise ValueError("an invocation preimage has exactly the seven named fields")
    return json.dumps(preimage, sort_keys=True, separators=(",", ":")).encode()


def invocation_digest(**fields_: Any) -> str:
    """sha256 of the canonical preimage. A call within an attempt keeps it; a new attempt differs."""
    return hashlib.sha256(_canonical(invocation_preimage(**fields_))).hexdigest()


class _Store(Protocol):
    directory: Path


def _put_once(folder: Path, name: str, raw: bytes, what: str) -> None:
    """Create-once, byte-compared on repeat (the ``execution._put_once`` rule)."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    if path.exists():
        if path.read_bytes() != raw:
            raise AuditCorrupt(f"Existing {what} is corrupt")
        return
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp-", dir=folder)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    _fsync_dir(folder)


def retain_preimage(store: _Store, preimage: Mapping[str, Any]) -> str:
    """Write the preimage at ``owner-run-audit/invocations/<digest>``; return the digest."""
    raw = _canonical(preimage)
    digest = hashlib.sha256(raw).hexdigest()
    _put_once(store.directory / AUDIT / INVOCATIONS, digest, raw, "invocation preimage")
    return digest


# ---------------------------------------------------------------- recordings


def _error_response(error: ProviderError, status: int | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": _KIND_NAME[error.kind],
        "error_class": error.error_class,
        "http_status": error.http_status if error.http_status is not None else status,
    }
    if error.usage is not None:
        out["usage"] = {f.name: getattr(error.usage, f.name) for f in fields(Usage)}
    if error.billed_usd is not None:
        out["billed_usd"] = str(error.billed_usd)
    return out


def export_recording(run_dir: Path, out: Path, redactor: Redactor) -> int:
    """Rebuild a recording file from ``calls.jsonl`` plus ``raw/``, re-parsing each archived body
    with the provider's mapper. Returns the number of lines written. A record with no http status
    has no body and exports as a ``not_sent`` / ``sent_unknown`` error with ``http_status`` null;
    any other record without its raw body raises ``RawMissing``. The ``redactor`` is the caller's; this never reads the environment."""
    run = Path(run_dir)
    responses: dict[tuple[str, int], dict[str, Any]] = {}
    for item in CallLog(run, redactor).records():
        rec = CallRecord.model_validate_json(json.dumps(item))
        key = (rec.invocation_digest, rec.call_index)
        if rec.http_status is None:
            # Ruled format: no status only for not_sent / sent_unknown. An unknown charge means the
            # request was held and counted (sent_unknown); a computed zero means nothing was sent.
            if rec.error_class is None:
                raise ValueError(f"record {key} has no status and no error_class")
            responses[key] = {
                "kind": "sent_unknown" if rec.cost_status == "unknown" else "not_sent",
                "error_class": rec.error_class,
                "http_status": None,
            }
            continue
        path = run / "raw" / f"{rec.invocation_digest}-{rec.call_index}.json"
        if not path.is_file():
            raise RawMissing(path.name)
        stored = load_json(path.read_text(encoding="utf-8"))
        body = stored.encode() if isinstance(stored, str) else dump_json(stored).encode()
        provider: Any = rec.provider
        outcome = parse(provider, rec.http_status, body, {}, redactor)
        response = (
            _error_response(outcome, rec.http_status)
            if isinstance(outcome, ProviderError)
            else turn_to_json(outcome)
        )
        if key in responses and dump_json(responses[key]) != dump_json(response):
            raise ValueError(f"conflicting records for {key}")
        responses[key] = response
    lines = [
        dump_json({"invocation_digest": d, "call_index": i, "response": r}) + "\n"
        for (d, i), r in responses.items()
    ]
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("".join(lines))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return len(lines)


__all__ = [
    "AuditCorrupt",
    "CallLog",
    "CallRecord",
    "RawExists",
    "RawMissing",
    "ToolCallRecord",
    "export_recording",
    "invocation_digest",
    "invocation_preimage",
    "retain_preimage",
]
