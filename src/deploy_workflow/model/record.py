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

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from deploy_vii.contracts import Contract, Hash
from deploy_workflow.model.pricing import CostStatus, money_text, refusal_values
from deploy_workflow.model.providers import ProviderError, parse
from deploy_workflow.model.redact import KEY_PATTERN, REPLACEMENT, Redactor
from deploy_workflow.model.turn import (
    Turn,
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
_MAPPER_SHAPE_ERRORS = (
    TypeError,
    AttributeError,
    KeyError,
    IndexError,
    ValueError,
    ArithmeticError,
)
_PROVIDERS: tuple[Any, ...] = ("openai", "anthropic", "openrouter")
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


class RawExists(FileExistsError):
    """A raw body was already archived for this (digest, call_index); never overwritten."""


class RawMissing(LookupError):
    """A record has no archived raw body to rebuild its recording from."""


class TornLog(RuntimeError):
    """``calls.jsonl`` does not end in a newline: a crash left half a line. Nothing is appended
    until a person repairs it; gluing a record onto the torn line would lose both."""


class RecordInvalid(ValueError):
    """A record failed validation. The message names fields and reasons, never the input."""


class ExportMismatch(ValueError):
    """A record and its archived body, or the record itself, do not agree on ``field``."""

    def __init__(self, digest: str, call_index: int, field: str) -> None:
        super().__init__(f"record {digest}-{call_index} disagrees with its archive on {field}")
        self.digest = digest
        self.call_index = call_index
        self.field = field


class AuditCorrupt(ValueError):
    """Bytes already at an audit path differ from the bytes that belong there."""


class ToolCallRecord(Contract):
    model_config = ConfigDict(hide_input_in_errors=True)

    name: str
    arguments_sha256: Hash
    result_bytes: int | None = Field(ge=0)
    refusal_code: str | None


def _money_field(value: Decimal) -> str:
    """The one money text for a record or its export: zero is written ``0`` (not ``-0``/``0.00``)."""
    return "0" if value == 0 else money_text(value)


def _where(error: Mapping[str, Any]) -> str:
    """An error's location. An ``extra_forbidden`` error's last ``loc`` element is the input's own
    field name, which may be a key, so a fixed placeholder replaces it; other elements are
    redacted by pattern."""
    loc = [KEY_PATTERN.sub(REPLACEMENT, str(part)) for part in error["loc"]]
    if error["type"] == "extra_forbidden":
        loc[-1] = "unexpected field"
    return ".".join(loc)


def _invalid(error: ValidationError) -> RecordInvalid:
    found = error.errors(include_input=False, include_url=False, include_context=False)
    return RecordInvalid("; ".join(f"{_where(e)}: {e['msg']}" for e in found))


def _redact(redactor: Redactor, value: Any) -> Any:
    if isinstance(value, str):
        return redactor.text(value)
    if isinstance(value, BaseModel):
        return type(value)(**_redact(redactor, value.model_dump()))
    if isinstance(value, dict):
        return {k: _redact(redactor, v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return tuple(_redact(redactor, v) for v in value)
    return value


def arguments_sha256(arguments: Mapping[str, Any]) -> str:
    """The one definition of a tool call's ``arguments_sha256``: sha256 of the compact JSON text
    ``turn.dump_json`` writes for the parsed arguments."""
    return hashlib.sha256(dump_json(arguments).encode()).hexdigest()


def strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [s for item in value.values() for s in strings(item)]
    if isinstance(value, list | tuple):
        return [s for item in value for s in strings(item)]
    return []


# ponytail: drop this alias once model_testing/records.py imports ``strings``.
_strings = strings


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
    reserved_usd: Decimal = Field(ge=0)
    settled_usd: Decimal | None = Field(ge=0)
    cost_status: CostStatus
    tool_calls: tuple[ToolCallRecord, ...]
    submit_sha256: Hash | None
    error_class: str | None
    error: str | None

    @field_validator("attempt", mode="before")
    @classmethod
    def _attempt_is_int(cls, value: Any) -> Any:
        # Literal[0, 1] accepts True, False and int subclasses because they equal 1 and 0.
        if type(value) is not int:
            raise PydanticCustomError("attempt_type", "attempt must be the integer 0 or 1")
        return value

    @field_serializer("reserved_usd", "settled_usd")
    def _money(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return _money_field(value)

    @model_validator(mode="after")
    def _checked(self) -> CallRecord:
        if (self.cost_status == "unknown") != (self.settled_usd is None):
            raise ValueError("settled_usd is None exactly when cost_status is unknown")
        for text in strings(self.model_dump(mode="json")):
            if KEY_PATTERN.search(text):
                raise ValueError("a record field holds key material")  # never the value
        return self

    @classmethod
    def build(cls, redactor: Redactor, **values: Any) -> CallRecord:
        """Construct after redacting every string value: ``error`` (a string, or an exception
        formatted with its chain) and the provider-supplied ids, models and tool-call fields.
        A key-shaped value is redacted, not refused, so the call's record can still be written.
        A validation failure is raised as ``RecordInvalid`` without the input."""
        error = values.get("error")
        if isinstance(error, BaseException):
            values["error"] = redactor.exception(error)
        elif isinstance(error, str):
            values["error"] = redactor.text(error)
        clean = {name: _redact(redactor, value) for name, value in values.items()}
        try:
            clean["tool_calls"] = tuple(
                ToolCallRecord(**c) if isinstance(c, dict) else c
                for c in clean.get("tool_calls", ())
            )
            return cls(**clean)
        except ValidationError as error:
            invalid = _invalid(error)
        raise invalid  # outside the handler: no chained ValidationError, which holds the input

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
        """Redact the record JSON, then write one fsynced line under an exclusive flock. A torn
        tail (no final newline) is refused: ``TornLog``."""
        clean = self._redactor.json_value(record.model_dump(mode="json"))
        data = (json.dumps(clean) + "\n").encode()
        self._dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._calls, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            size = os.fstat(fd).st_size
            if size and os.pread(fd, 1, size - 1) != b"\n":
                raise TornLog(f"{self._calls.name} ends mid-line; repair it before appending")
            _write_all(fd, data)
            os.fsync(fd)
            if size == 0:
                _fsync_dir(self._dir)  # the file is new: make its directory entry durable
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
        # ponytail: one writer per (module, step, attempt): the tool loop is sequential, so the
        # read here and the append later need no common lock. Upgrade when calls of one step can
        # overlap: read the index and append under one flock.
        taken = [
            r["call_index"]
            for r in self.records()
            if (r["module_id"], r["step_id"], r["attempt"]) == (module_id, step_id, attempt)
        ]
        return max(taken, default=-1) + 1

    def _withheld(self, body: bytes, error_class: str | None) -> str | None:
        """The reason this body is archived as a placeholder, or None when redaction suffices."""
        if error_class == "KeyReflected":
            return "KeyReflected"
        try:
            body.decode("utf-8")
        except UnicodeDecodeError:
            return "InvalidUtf8"
        if b"\x00" in body:  # UTF-16/32 of ASCII decodes as UTF-8 with NULs; a UTF-8 redactor
            return "InvalidUtf8"  # cannot see a key in it, and no JSON text holds a raw NUL
        # A key that is whole only after decoding (JSON escapes, SSE deltas joined) survives the
        # byte redaction; ask the provider mappers, as the live adapter did, whether one remains.
        redacted = self._redactor.bytes_(body)
        for provider in _PROVIDERS:
            try:
                outcome = parse(provider, 200, redacted, {}, self._redactor)
            except _MAPPER_SHAPE_ERRORS:
                # fail closed: a mapper that crashes on this body cannot say whether a key is
                # left in it, so the body is not archived. Root cause is in providers.py.
                return "MapperError"
            if isinstance(outcome, ProviderError) and outcome.error_class == "KeyReflected":
                return "KeyReflected"
        return None

    def write_raw(
        self, digest: str, call_index: int, body: bytes, *, error_class: str | None = None
    ) -> Path:
        """Archive the redacted body at ``raw/<digest>-<call_index>.json``, create-once.

        A key-reflected or non-UTF-8 body is withheld: the archive holds the JSON string
        ``[withheld: <reason>; <n> bytes]``. The file is written and fsynced under a temporary
        name and linked into place, so a crash leaves no half-written archive."""
        if not _DIGEST.fullmatch(digest):
            raise ValueError("digest must be 64 lowercase hex characters")
        if isinstance(call_index, bool) or not isinstance(call_index, int) or call_index < 0:
            raise ValueError("call_index must be a non-negative integer")
        reason = self._withheld(body, error_class)
        if reason is not None:
            stored = json.dumps(f"[withheld: {reason}; {len(body)} bytes]")
        else:
            text = body.decode("utf-8")
            try:
                stored = dump_json(self._redactor.json_value(load_json(text)))
                if stored.startswith('"'):  # a bare JSON string body: keep its quotes, so export
                    stored = json.dumps(stored)  # can tell it from a text body (stored unquoted)
            except (TurnError, RecursionError):  # not JSON, or too deep to walk: keep the text
                stored = json.dumps(self._redactor.text(text))
        if not self._raw.exists():
            self._raw.mkdir(parents=True, exist_ok=True)
            _fsync_dir(self._dir)
        path = self._raw / f"{digest}-{call_index}.json"
        descriptor, temporary = tempfile.mkstemp(prefix=".tmp-", dir=self._raw)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(stored.encode())
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise RawExists(path.name) from None
        finally:
            Path(temporary).unlink(missing_ok=True)
        _fsync_dir(self._raw)
        return path


# ---------------------------------------------------------------- invocation digest


def invocation_preimage(
    *,
    run_id: str,
    module_id: str,
    step_id: str,
    attempt: int,
    upstream_hashes: list[str] | tuple[str, ...] | str,
    prompt_sha256: str,
    method_version: str = METHOD_VERSION,
) -> dict[str, Any]:
    if type(upstream_hashes) is str:
        raise ValueError("upstream_hashes is a list of hashes, not a string")
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


def _text_field(name: str, value: object) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"preimage {name} must be a non-empty string")
    if KEY_PATTERN.search(value):
        raise ValueError(f"preimage {name} holds key material")


def _hash_field(name: str, value: object) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ValueError(f"preimage {name} must be 64 lowercase hex characters")


def _checked_canonical(preimage: Mapping[str, Any]) -> bytes:
    """The canonical bytes of a validated preimage; ``upstream_hashes`` sorted as the digest does."""
    normal = dict(preimage)
    hashes = normal.get("upstream_hashes")
    if isinstance(hashes, list | tuple):
        normal["upstream_hashes"] = sorted(hashes, key=str)
    raw = _canonical(normal)
    for name in ("run_id", "module_id", "step_id", "method_version"):
        _text_field(name, normal[name])
    if type(normal["attempt"]) is not int or normal["attempt"] not in (0, 1):
        raise ValueError("preimage attempt must be 0 or 1")
    _hash_field("prompt_sha256", normal["prompt_sha256"])
    if type(normal["upstream_hashes"]) is not list:
        raise ValueError("preimage upstream_hashes must be a list")
    for item in normal["upstream_hashes"]:
        _hash_field("upstream_hashes", item)
    return raw


def invocation_digest(**fields_: Any) -> str:
    """sha256 of the canonical preimage. A call within an attempt keeps it; a new attempt differs."""
    return hashlib.sha256(_checked_canonical(invocation_preimage(**fields_))).hexdigest()


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
    raw = _checked_canonical(preimage)
    digest = hashlib.sha256(raw).hexdigest()
    _put_once(store.directory / AUDIT / INVOCATIONS, digest, raw, "invocation preimage")
    return digest


# ---------------------------------------------------------------- recordings


# The closed set of stop classes the tool loop writes into the record of a reply that was ok:
# the reply parsed as a turn, then the loop stopped on it. Such a record exports as the ok turn.
LOOP_STOPS: frozenset[str] = frozenset({"NoSubmit", "CallLimit", "WorkflowError", "BadTurn"})

# The class of a record whose ``complete`` raised: the call may have been sent, the charge is unknown.
ADAPTER_ERROR = "AdapterError"

_TRANSPORT_CLASSES = frozenset(
    {"ConnectTimeout", "IdleTimeout", "OverallTimeout", "TransportError", ADAPTER_ERROR}
)


_RECORDED_TOKENS = (
    "input_tokens",
    "cached_read_tokens",
    "cache_write_tokens",  # the 5m/1h split is not recorded (B11); see _split_from_body
    "output_tokens",
    "reasoning_tokens",
)


def _usage_of(rec: CallRecord) -> dict[str, int | None]:
    """The five recorded token fields; an error reply's usage object leaves the split None."""
    return {name: getattr(rec, name) for name in _RECORDED_TOKENS}


def _usage_object(rec: CallRecord) -> dict[str, int | None]:
    return {f.name: getattr(rec, f.name, None) for f in fields(Usage)}


def _split_from_body(
    run: Path, rec: CallRecord, status: int, redactor: Redactor
) -> tuple[int | None, int | None]:
    """The Anthropic 5m/1h cache-write split of a usage-bearing error reply, from its raw body.

    The record keeps five token fields (B11), so the split is read back by re-parsing the archived
    body. It is taken only when the parsed usage agrees with the five recorded fields (else
    ``ExportMismatch``). A missing or withheld body, or one that parses to no usage, leaves the
    split None and the replay prices the call unknown."""
    path = run / "raw" / f"{rec.invocation_digest}-{rec.call_index}.json"
    if rec.provider != "anthropic" or not path.is_file() or path.stat().st_size == 0:
        return None, None
    parsed = parse("anthropic", status, _archived_body(path, rec), {}, redactor)
    if not isinstance(parsed, ProviderError) or parsed.usage is None:
        return None, None
    if _usage_of(rec) != {k: getattr(parsed.usage, k) for k in _RECORDED_TOKENS}:
        raise ExportMismatch(rec.invocation_digest, rec.call_index, "usage")
    return parsed.usage.cache_write_5m_tokens, parsed.usage.cache_write_1h_tokens


def _error_response(
    rec: CallRecord, error_class: str, run: Path, redactor: Redactor
) -> dict[str, Any]:
    """An error reply from the record's own fields. Only a usage-bearing reply also consults the
    raw body, for the cache-write split the record does not keep."""
    key = (rec.invocation_digest, rec.call_index)
    unknown = rec.cost_status == "unknown"
    if rec.http_status is None:
        if rec.cost_status == "billed":
            raise ExportMismatch(*key, "cost_status")
        kind = "sent_unknown" if error_class in _TRANSPORT_CLASSES else "not_sent"
        if (kind == "sent_unknown") != unknown:
            raise ExportMismatch(*key, "cost_status")
        return {"kind": kind, "error_class": error_class, "http_status": None}
    has_tokens = any(v is not None for v in _usage_of(rec).values())
    out: dict[str, Any] = {"error_class": error_class, "http_status": rec.http_status}
    # Usage first: a ProviderError carries usage only for SentChargeUsage, and a usage-bearing
    # reply whose charge prices as unknown is still a sent_usage reply.
    if has_tokens or rec.cost_status == "billed":
        out["kind"] = "sent_usage"
        out["usage"] = _usage_object(rec)
        out["usage"]["cache_write_5m_tokens"], out["usage"]["cache_write_1h_tokens"] = (
            _split_from_body(run, rec, rec.http_status, redactor)
        )
    elif unknown:
        out["kind"] = "sent_unknown"
    else:
        out["kind"] = "sent_known"
        if not 400 <= rec.http_status <= 499:
            raise ExportMismatch(*key, "http_status")
    if rec.cost_status == "billed" and rec.settled_usd is not None:
        out["billed_usd"] = _money_field(rec.settled_usd)
    return {"kind": out.pop("kind"), **out}


def _refuse_forged_error(run: Path, rec: CallRecord, redactor: Redactor) -> None:
    """An error record's archived body, when there is one, must not parse as an ok turn: a body
    swapped in for an error record is refused. The response still comes from the record. A
    ``KeyReflected`` record is exempt: its body, once redacted, can legitimately parse as a turn."""
    path = run / "raw" / f"{rec.invocation_digest}-{rec.call_index}.json"
    if rec.error_class == "KeyReflected" or rec.http_status is None:
        return
    if not path.is_file() or path.stat().st_size == 0:
        return
    body = _archived_body(path, rec)
    provider: Any = rec.provider
    if isinstance(parse(provider, rec.http_status, body, {}, redactor), Turn):
        raise ExportMismatch(rec.invocation_digest, rec.call_index, "outcome")


def _archived_body(path: Path, rec: CallRecord) -> bytes:
    try:
        stored = load_json(path.read_text(encoding="utf-8"))
    except (TurnError, UnicodeDecodeError):
        raise ExportMismatch(rec.invocation_digest, rec.call_index, "raw") from None
    body = stored.encode() if isinstance(stored, str) else dump_json(stored).encode()
    return body


def _ok_response(
    run: Path, rec: CallRecord, redactor: Redactor, *, prefix: bool = False
) -> dict[str, Any]:
    """Re-parse the archived body; it must be a turn that says what the record says. With
    ``prefix`` (the loop stopped on this ok reply) the record lists only the tool calls it
    reached: the first ones of the turn."""
    digest, index = rec.invocation_digest, rec.call_index
    path = run / "raw" / f"{digest}-{index}.json"
    if not path.is_file() or path.stat().st_size == 0:
        raise RawMissing(path.name)
    body = _archived_body(path, rec)
    provider: Any = rec.provider
    if rec.http_status is None:
        raise ExportMismatch(digest, index, "http_status")
    outcome = parse(provider, rec.http_status, body, {}, redactor)
    if not isinstance(outcome, Turn):
        raise ExportMismatch(digest, index, "outcome")
    if _usage_of(rec) != {k: getattr(outcome.usage, k) for k in _RECORDED_TOKENS}:
        raise ExportMismatch(digest, index, "usage")
    if rec.cost_status == "billed" and outcome.billed_usd != rec.settled_usd:
        raise ExportMismatch(digest, index, "billed_usd")
    if rec.request_id != outcome.request_id:
        raise ExportMismatch(digest, index, "request_id")
    if rec.reported_model != outcome.reported_model:
        raise ExportMismatch(digest, index, "reported_model")
    seen = [(c.name, c.arguments_sha256) for c in rec.tool_calls]
    sent = [(c.name, arguments_sha256(c.arguments)) for c in outcome.tool_calls]
    if seen != (sent[: len(seen)] if prefix else sent):
        raise ExportMismatch(digest, index, "tool_calls")
    return turn_to_json(outcome)


def export_recording(run_dir: Path, out: Path, redactor: Redactor) -> int:
    """Rebuild a recording file (the ``RecordedAdapter`` line format) from ``calls.jsonl`` plus
    ``raw/``. Returns the number of lines written.

    A record whose ``error_class`` is a ``LOOP_STOPS`` class with a 2xx status is an ok reply the
    loop stopped on: it exports as the ok turn, its tool calls a prefix of the turn's. Any other
    error record (``error_class`` set) exports from its own fields and is never re-parsed. An
    ok record re-parses its archived body with the provider mapper and must agree with it, else
    ``ExportMismatch``; a missing or empty body is ``RawMissing``. A null-status record's kind
    comes from its ``error_class`` and must agree with ``cost_status``. The ``redactor`` is the
    caller's; this never reads the environment."""
    run = Path(run_dir)
    responses: dict[tuple[str, int], dict[str, Any]] = {}
    for item in CallLog(run, redactor).records():
        invalid: RecordInvalid | None = None
        try:
            rec = CallRecord.model_validate_json(json.dumps(item))
        except ValidationError as error:
            invalid = _invalid(error)
        if invalid is not None:
            raise invalid  # outside the handler: no chained ValidationError
        key = (rec.invocation_digest, rec.call_index)
        stopped_ok = (
            rec.error_class in LOOP_STOPS
            and rec.http_status is not None
            and 200 <= rec.http_status < 300
        )
        if rec.error_class is None or stopped_ok:
            response = _ok_response(
                run, rec, redactor, prefix=stopped_ok and rec.error_class != "NoSubmit"
            )
        else:
            _refuse_forged_error(run, rec, redactor)
            response = _error_response(rec, rec.error_class, run, redactor)
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
    "ADAPTER_ERROR",
    "LOOP_STOPS",
    "AuditCorrupt",
    "CallLog",
    "CallRecord",
    "ExportMismatch",
    "RawExists",
    "RawMissing",
    "RecordInvalid",
    "ToolCallRecord",
    "TornLog",
    "arguments_sha256",
    "export_recording",
    "invocation_digest",
    "invocation_preimage",
    "retain_preimage",
    "strings",
]
