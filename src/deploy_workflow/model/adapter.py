"""Recorded and live model adapters, and the R2 live-pause gate.

``complete`` sends at most one request and never retries or resends: resend (the 402 wait,
repair, transient retry) belongs to the loop. A recorded adapter has ``ruling is None`` and reads
no environment. A live adapter runs ``check_live_gate`` first, before it touches any environment
mapping or builds a ``Redactor``; only the first ``complete`` reads the three key variables.

The gate is a tripwire against an accidental live call, not an authenticator: a file that
says ``by: user`` proves nothing about who wrote it.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal, Protocol, cast

from deploy_workflow.model.providers import (
    ErrorKind,
    ProviderConfigError,
    ProviderError,
    build,
    error_from_transport,
    parse,
    retry_after_seconds,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import Request, Response, TransportError, https_transport
from deploy_workflow.model.turn import (
    _USAGE_KEYS,
    ModelSpec,
    Turn,
    TurnError,
    TurnRequest,
    Usage,
    _exact_keys,
    load_json,
    turn_from_json,
)

ReplyKind = Literal["ok", "not_sent", "sent_known", "sent_usage", "sent_unknown"]
_ERROR_KINDS: tuple[str, ...] = ("not_sent", "sent_known", "sent_usage", "sent_unknown")
_KIND_OF: Mapping[ErrorKind, ReplyKind] = {
    ErrorKind.NOT_SENT: "not_sent",
    ErrorKind.SENT_CHARGE_KNOWN: "sent_known",
    ErrorKind.SENT_CHARGE_USAGE: "sent_usage",
    ErrorKind.SENT_CHARGE_UNKNOWN: "sent_unknown",
}
KEY_VARIABLES: Mapping[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
LIVE_RULINGS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "rulings"
_PAUSE_LIFT = "live-provider-pause"
_RULING_KEYS = ("lifts", "by", "date", "configs")
_RULING_LINE = re.compile(r"^[ \t]*(lifts|by|date|configs):[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class LivePauseInForce(Exception):
    """No user ruling lifts the live-provider pause for this configuration."""


class RecordingError(ValueError):
    """A recording file or line is malformed."""


class RecordingConflict(RecordingError):
    """Two recordings share (invocation_digest, call_index) with different responses."""


class RecordingMissing(LookupError):
    """No recording for this call; never defaulted."""

    def __init__(self, digest: str, call_index: int) -> None:
        super().__init__(f"no recording for digest {digest} call_index {call_index}")
        self.digest = digest
        self.call_index = call_index


@dataclass(frozen=True)
class AdapterReply:
    """One provider exchange. ``turn`` is set exactly for ``ok``; ``usage`` for ``ok`` and
    ``sent_usage``. Times are epoch seconds; ``first_byte_at`` is None when the transport does
    not report it (the bounded transport returns the whole reply at once)."""

    kind: ReplyKind
    turn: Turn | None
    raw: bytes | None
    http_status: int | None
    error_class: str | None
    first_byte_at: float | None
    started_at: float | None
    finished_at: float | None
    usage: Usage | None = None
    billed_usd: Decimal | None = None
    retry_after: int | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if self.kind != "ok" and self.kind not in _ERROR_KINDS:
            raise ValueError(f"unknown reply kind {self.kind!r}")
        if (self.kind == "ok") != (self.turn is not None):
            raise ValueError("turn is present exactly when kind is ok")
        if self.kind == "sent_usage" and self.usage is None:
            raise ValueError("sent_usage needs usage")


class ModelAdapter(Protocol):
    config_id: str
    ruling: Path | None

    def complete(
        self,
        request: TurnRequest,
        *,
        invocation_digest: str,
        call_index: int,
        reservation_id: str,
    ) -> AdapterReply: ...


# ---------------------------------------------------------------- the R2 gate


@dataclass(frozen=True)
class GateResult:
    path: Path
    sha256: str
    date: Date


def check_live_gate(
    model: ModelSpec, ruling: Path, *, rulings_root: Path | None = None
) -> GateResult:
    """Refuse unless ``ruling`` resolves (symlinks and ``..`` followed) inside the rulings root
    and has the lines ``lifts: live-provider-pause``, ``by: user``, ``date: YYYY-MM-DD`` and a
    ``configs:`` line naming ``model.config_id`` as a whole whitespace/comma-separated token.
    A tripwire, not an authenticator."""
    root = (LIVE_RULINGS_ROOT if rulings_root is None else rulings_root).resolve()
    try:
        path = Path(ruling).resolve(strict=True)
        data = path.read_bytes() if path.is_file() else None
        text = None if data is None else data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise LivePauseInForce(f"ruling unreadable: {type(error).__name__}") from None
    if data is None or text is None:
        raise LivePauseInForce("the ruling is not a file")
    if not path.is_relative_to(root):
        raise LivePauseInForce("the ruling is not under docs/rulings")
    found: dict[str, list[str]] = {key: [] for key in _RULING_KEYS}
    for match in _RULING_LINE.finditer(text):
        found[match.group(1)].append(match.group(2))
    for key in _RULING_KEYS:
        if len(found[key]) != 1:
            raise LivePauseInForce(f"the ruling needs exactly one {key}: line")
    if found["lifts"][0] != _PAUSE_LIFT:
        raise LivePauseInForce("the ruling does not lift live-provider-pause")
    if found["by"][0] != "user":
        raise LivePauseInForce("the ruling is not by: user")
    raw_date = found["date"][0]
    if not _ISO_DATE.fullmatch(raw_date):
        raise LivePauseInForce("the ruling date is not YYYY-MM-DD")
    try:
        day = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        raise LivePauseInForce("the ruling date is not a valid date") from None
    if model.config_id not in [t for t in re.split(r"[\s,]+", found["configs"][0]) if t]:
        raise LivePauseInForce(f"the ruling does not list {model.config_id!r}")
    return GateResult(path, hashlib.sha256(data).hexdigest(), day)


# ---------------------------------------------------------------- recorded


def _reply_from_error_json(obj: object) -> AdapterReply:
    keys = {"kind", "error_class", "http_status"}
    if isinstance(obj, Mapping):
        keys |= set(obj) & {"usage", "billed_usd"}
    data = _exact_keys("error response", obj, frozenset(keys))
    kind, error_class, status = data["kind"], data["error_class"], data["http_status"]
    if kind not in _ERROR_KINDS:
        raise TurnError(f"unknown error kind {kind!r}")
    if not isinstance(error_class, str):
        raise TurnError("error_class must be a string")
    if isinstance(status, bool) or not isinstance(status, int):
        raise TurnError("http_status must be an integer")
    usage: Usage | None = None
    if "usage" in data:
        usage_obj = _exact_keys("usage", data["usage"], _USAGE_KEYS)
        usage = Usage(**{k: usage_obj[k] for k in _USAGE_KEYS})
    if (kind == "sent_usage") != (usage is not None):
        raise TurnError("usage is present exactly when kind is sent_usage")
    billed: Decimal | None = None
    if "billed_usd" in data:
        raw = data["billed_usd"]
        if not isinstance(raw, str):
            raise TurnError("billed_usd must be a decimal string")
        try:
            billed = Decimal(raw)
        except InvalidOperation:
            raise TurnError("billed_usd is not a decimal string") from None
        if not billed.is_finite() or billed < 0:
            raise TurnError("billed_usd must be finite and non-negative")
    return AdapterReply(
        cast(ReplyKind, kind), None, None, status, error_class, None, None, None, usage, billed
    )


def _reply_from_json(obj: object) -> AdapterReply:
    if isinstance(obj, Mapping) and "kind" in obj:
        return _reply_from_error_json(obj)
    turn = turn_from_json(obj)
    return AdapterReply(
        "ok", turn, None, turn.http_status, None, None, None, None, turn.usage, turn.billed_usd
    )


_ENVELOPE_KEYS = frozenset({"invocation_digest", "call_index", "response"})


class RecordedAdapter:
    ruling: Path | None = None

    def __init__(self, model: ModelSpec, replies: Mapping[tuple[str, int], AdapterReply]) -> None:
        self.config_id = model.config_id
        self._replies = dict(replies)

    def complete(
        self,
        request: TurnRequest,
        *,
        invocation_digest: str,
        call_index: int,
        reservation_id: str,
    ) -> AdapterReply:
        try:
            return self._replies[(invocation_digest, call_index)]
        except KeyError:
            raise RecordingMissing(invocation_digest, call_index) from None


def recorded_adapter(model: ModelSpec, recordings: Path) -> RecordedAdapter:
    """Read every ``*.jsonl`` under ``recordings``; no environment, no key."""
    root = Path(recordings)
    if not root.is_dir():
        raise RecordingError(f"recordings directory {root} does not exist")
    replies: dict[tuple[str, int], AdapterReply] = {}
    responses: dict[tuple[str, int], object] = {}
    for path in sorted(root.rglob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise RecordingError(f"{path}: unreadable: {type(error).__name__}") from None
        for number, text in enumerate(lines, start=1):
            if not text.strip():
                continue
            where = f"{path.name} line {number}"
            try:
                envelope = _exact_keys("recording", load_json(text), _ENVELOPE_KEYS)
                digest, index = envelope["invocation_digest"], envelope["call_index"]
                if not isinstance(digest, str) or not digest:
                    raise TurnError("invocation_digest must be a non-empty string")
                if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                    raise TurnError("call_index must be a non-negative integer")
                reply = _reply_from_json(envelope["response"])
            except TurnError as error:
                raise RecordingError(f"{where}: {error}") from None
            key = (digest, index)
            if key in responses and responses[key] != envelope["response"]:
                raise RecordingConflict(f"{where}: conflicting response for {key}")
            responses[key] = envelope["response"]
            replies[key] = reply
    return RecordedAdapter(model, replies)


# ---------------------------------------------------------------- live


class LiveAdapter:
    def __init__(
        self,
        model: ModelSpec,
        ruling: Path,
        gate: GateResult,
        transport: Callable[[Request], Response],
        environ: Mapping[str, str] | None,
        clock: Callable[[], float],
    ) -> None:
        self.config_id = model.config_id
        self.ruling: Path | None = ruling
        self.gate = gate
        self._model = model
        self._transport = transport
        self._environ = environ  # None: os.environ, read only at the first complete
        self._clock = clock
        self._cached: tuple[str, str | None, Redactor] | None = None

    def _credentials(self) -> tuple[str, str | None, Redactor]:
        """The key variable's name and value and the redactor, read once from the mapping on
        the first call (after the gate passed at construction) and kept for later calls. The
        redactor covers all three provider keys by exact value."""
        if self._cached is None:
            environ = os.environ if self._environ is None else self._environ
            name = KEY_VARIABLES[self._model.provider]
            redactor = Redactor.from_environ(environ)
            self._cached = (name, environ.get(name) or None, redactor)
        return self._cached

    def complete(
        self,
        request: TurnRequest,
        *,
        invocation_digest: str,
        call_index: int,
        reservation_id: str,
    ) -> AdapterReply:
        """Send one request; never retry. The key variables are read on the first call only."""
        started = self._clock()
        name, key, redactor = self._credentials()
        if key is None:
            return AdapterReply(
                "not_sent", None, None, None, "KeyMissing", None, started, self._clock(),
                message=f"{name} is not set or empty",
            )  # fmt: skip
        try:
            built = build(self._model, request, key)
        except ProviderConfigError as error:
            return AdapterReply(
                "not_sent", None, None, None, type(error).__name__, None, started, self._clock(),
                message=redactor.text(str(error)),
            )  # fmt: skip
        headers: Mapping[str, str] = {}
        try:
            response = self._transport(built)
        except TransportError as exc:
            outcome = error_from_transport(self._model.provider, exc, redactor)
            raw = redactor.bytes_(exc.partial) or None
            status = None
        else:
            headers = response.headers
            outcome = parse(self._model.provider, response.status, response.body, headers, redactor)
            raw = redactor.bytes_(response.body)
            status = response.status
        finished = self._clock()
        if isinstance(outcome, Turn):
            return AdapterReply(
                "ok", outcome, raw, outcome.http_status, None, None, started, finished,
                outcome.usage, outcome.billed_usd,
            )  # fmt: skip
        return _reply_from_error(outcome, raw, status, headers, started, finished)


def _reply_from_error(
    error: ProviderError,
    raw: bytes | None,
    status: int | None,
    headers: Mapping[str, str],
    started: float,
    finished: float,
) -> AdapterReply:
    http_status = error.http_status if error.http_status is not None else status
    return AdapterReply(
        _KIND_OF[error.kind], None, raw, http_status, error.error_class, None, started, finished,
        error.usage, error.billed_usd,
        retry_after_seconds(headers) if http_status == 402 else None,
        error.message,
    )  # fmt: skip


def live_adapter(
    model: ModelSpec,
    ruling: Path,
    *,
    transport: Callable[[Request], Response] = https_transport,
    environ: Mapping[str, str] | None = None,
    clock: Callable[[], float] = time.time,
) -> LiveAdapter:
    """Run the R2 gate first. Nothing reads or builds from the environment before it passes,
    and even after it the environment is read only by ``complete`` (F11). ``environ=None``
    means ``os.environ``, looked up then."""
    gate = check_live_gate(model, ruling)
    return LiveAdapter(model, Path(ruling), gate, transport, environ, clock)


__all__ = [
    "KEY_VARIABLES",
    "AdapterReply",
    "GateResult",
    "LiveAdapter",
    "LivePauseInForce",
    "ModelAdapter",
    "RecordedAdapter",
    "RecordingConflict",
    "RecordingError",
    "RecordingMissing",
    "check_live_gate",
    "live_adapter",
    "recorded_adapter",
]
