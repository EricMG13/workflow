"""Cap-enforcing budget with durable, create-once reservation markers (money code).

Layout, under the run's Execution directory (``owner_workflow.AUDIT``):

    owner-run-audit/reservations/<call_id>           {"usd", "config_id", "retry_of"}
    owner-run-audit/reservations/<call_id>.settled   {"status", "usd", "retryable"}

A reservation marker is written (``O_CREAT|O_EXCL``, ``fsync``) before ``reserve`` returns, so a
crash after a send leaves evidence. A new ``Budget`` over the same directory recomputes its
state from the markers. A reservation with no ``.settled`` marker at load is a crash-left unknown
charge: it stays held, is listed by ``unsettled``, and stops the run until settled or released
(an operator step); no ``retry_of`` may name it.

Meaning of the numbers: ``reserved`` is the sum of unsettled holds; ``spent`` is the actual
charges plus the full holds of unknown-charge calls. The cap check is
``reserved + spent + usd <= cap``.

Stops: an unknown charge or an overrun stops the run (``RunStopped``). The one exception is a
single ``retry_of`` reserve naming an unknown hold that the caller marked ``retryable`` (5xx or
cut stream); that retry lifts the stop of the hold it names, the hold itself stays counted. An
overrun is never retryable.
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from deploy_workflow.model.pricing import money_text, refusal_values

__all__ = [
    "Budget",
    "BudgetError",
    "BudgetExhausted",
    "DuplicateCall",
    "OverrunStop",
    "RetryUsed",
    "RunStopped",
    "money_text",
    "refusal_values",
]

AUDIT = "owner-run-audit"  # owner_workflow.AUDIT
RESERVATIONS = "reservations"
_SETTLED = ".settled"
_ID = re.compile(r"[A-Za-z0-9_-]+")


class BudgetError(RuntimeError):
    """The budget refuses or cannot trust its state."""


class BudgetExhausted(BudgetError):
    """The reservation would pass the cap; nothing was held."""


class RunStopped(BudgetError):
    """An unknown charge or an overrun stopped the run."""


class OverrunStop(RunStopped):
    """The actual charge was above the reservation; it is recorded in full."""


class RetryUsed(BudgetError):
    """The run's one retry was already taken."""


class DuplicateCall(BudgetError):
    """A reservation or settlement for this call id already exists."""


@dataclass(frozen=True)
class _Hold:
    usd: Decimal
    config_id: str
    retry_of: str | None


@dataclass(frozen=True)
class _Settlement:
    status: str  # settled | unknown | overrun | released
    usd: Decimal
    retryable: bool


def _decimal(name: str, value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal | int):
        raise BudgetError(f"{name} must be a Decimal or int, not {type(value).__name__}")
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0:
        raise BudgetError(f"{name} must be finite and non-negative")
    return amount


def _call_id(value: object) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise BudgetError("call_id must match [A-Za-z0-9_-]+")
    return value


def _write_once(path: Path, payload: dict[str, object]) -> None:
    """Create ``path`` exclusively, write, fsync the file and its directory."""
    data = json.dumps(payload, sort_keys=True).encode()
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise DuplicateCall(f"{path.name} already exists") from None
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view) :]
        os.fsync(fd)
    finally:
        os.close(fd)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _decimal_text(name: str, value: object) -> Decimal:
    if not isinstance(value, str):
        raise BudgetError(f"marker {name} is not a decimal string")
    try:
        return _decimal(name, Decimal(value))
    except InvalidOperation:
        raise BudgetError(f"marker {name} is not a decimal string") from None


def _read_marker(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise BudgetError(f"unreadable marker {path.name}: {error}") from None
    if not isinstance(data, dict):
        raise BudgetError(f"marker {path.name} is not an object")
    return data


class Budget:
    """Reserves against ``cap_usd``; ``run_dir`` is the run's Execution directory."""

    def __init__(self, cap_usd: Decimal, run_dir: Path) -> None:
        self._cap = _decimal("cap_usd", cap_usd)
        self._dir = Path(run_dir) / AUDIT / RESERVATIONS
        self._lock = threading.Lock()
        self._holds: dict[str, _Hold] = {}
        self._settled: dict[str, _Settlement] = {}
        self._crash_left: set[str] = set()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        names = sorted(p.name for p in self._dir.iterdir())
        for name in names:
            if name.endswith(_SETTLED):
                continue
            _call_id(name)
            raw = _read_marker(self._dir / name)
            retry_of = raw.get("retry_of")
            config_id = raw.get("config_id")
            if not isinstance(config_id, str) or not (
                retry_of is None or isinstance(retry_of, str)
            ):
                raise BudgetError(f"marker {name} has the wrong field types")
            self._holds[name] = _Hold(_decimal_text("usd", raw.get("usd")), config_id, retry_of)
        for name in names:
            if not name.endswith(_SETTLED):
                continue
            call_id = name[: -len(_SETTLED)]
            if call_id not in self._holds:
                raise BudgetError(f"settled marker {name} has no reservation")
            raw = _read_marker(self._dir / name)
            status, retryable = raw.get("status"), raw.get("retryable")
            if status not in ("settled", "unknown", "overrun", "released") or not isinstance(
                retryable, bool
            ):
                raise BudgetError(f"marker {name} has the wrong field types")
            self._settled[call_id] = _Settlement(
                str(status), _decimal_text("usd", raw.get("usd")), retryable
            )

        # A reservation with no .settled marker at load time may have been sent: unknown charge.
        self._crash_left = {c for c in self._holds if c not in self._settled}

    # -- state ------------------------------------------------------------------------

    @property
    def cap_usd(self) -> Decimal:
        return self._cap

    @property
    def reserved(self) -> Decimal:
        with self._lock:
            return self._reserved()

    @property
    def spent(self) -> Decimal:
        with self._lock:
            return self._spent()

    @property
    def unsettled(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(c for c in self._holds if c not in self._settled))

    def _reserved(self) -> Decimal:
        return sum((h.usd for c, h in self._holds.items() if c not in self._settled), Decimal(0))

    def _spent(self) -> Decimal:
        return sum((s.usd for s in self._settled.values()), Decimal(0))

    def _retried(self) -> set[str]:
        return {h.retry_of for h in self._holds.values() if h.retry_of is not None}

    def _stopped(self) -> bool:
        retried = self._retried()
        return bool(self._crash_left) or any(
            s.status == "overrun" or (s.status == "unknown" and c not in retried)
            for c, s in self._settled.items()
        )

    # -- operations -------------------------------------------------------------------

    def reserve(
        self, call_id: str, usd: Decimal, retry_of: str | None = None, *, config_id: str
    ) -> None:
        call_id = _call_id(call_id)
        amount = _decimal("usd", usd)
        if not isinstance(config_id, str) or not config_id:
            raise BudgetError("config_id must be a non-empty string")
        with self._lock:
            if retry_of is None:
                if self._stopped():
                    raise RunStopped("an unknown charge or an overrun stopped the run")
            else:
                self._check_retry(_call_id(retry_of))
            if self._reserved() + self._spent() + amount > self._cap:
                raise BudgetExhausted(
                    f"reserving {money_text(amount)} passes the cap {money_text(self._cap)}"
                )
            _write_once(
                self._dir / call_id,
                {"usd": str(amount), "config_id": config_id, "retry_of": retry_of},
            )
            self._holds[call_id] = _Hold(amount, config_id, retry_of)

    def _check_retry(self, retry_of: str) -> None:
        if self._crash_left:
            raise RunStopped("a reservation left unsettled by a crash stopped the run")
        if self._retried():
            raise RetryUsed("the run's one retry was already taken")
        settlement = self._settled.get(retry_of)
        if settlement is None or settlement.status != "unknown" or not settlement.retryable:
            raise RunStopped(f"{retry_of!r} is not a retryable unknown-charge hold")

    def settle(self, call_id: str, actual: Decimal | None, *, retryable: bool = False) -> None:
        """Replace the hold with ``actual`` (releasing the difference), or with ``None`` keep
        the full hold and stop. ``retryable`` marks an unknown charge from a 5xx or cut stream."""
        call_id = _call_id(call_id)
        with self._lock:
            hold = self._open_hold(call_id)
            if actual is None:
                self._record(call_id, _Settlement("unknown", hold.usd, bool(retryable)))
                return
            amount = _decimal("actual", actual)
            if amount > hold.usd:
                self._record(call_id, _Settlement("overrun", amount, False))
                raise OverrunStop(
                    f"{call_id}: actual {money_text(amount)} is above the reservation "
                    f"{money_text(hold.usd)}"
                )
            self._record(call_id, _Settlement("settled", amount, False))

    def release(self, call_id: str) -> None:
        """Free a not-sent or known-zero call. Never for a sent call of unknown charge."""
        call_id = _call_id(call_id)
        with self._lock:
            self._open_hold(call_id)
            self._record(call_id, _Settlement("released", Decimal(0), False))

    def _open_hold(self, call_id: str) -> _Hold:
        hold = self._holds.get(call_id)
        if hold is None:
            raise BudgetError(f"no reservation for {call_id!r}")
        if call_id in self._settled:
            raise DuplicateCall(f"{call_id!r} is already settled")
        return hold

    def _record(self, call_id: str, settlement: _Settlement) -> None:
        _write_once(
            self._dir / (call_id + _SETTLED),
            {
                "status": settlement.status,
                "usd": str(settlement.usd),
                "retryable": settlement.retryable,
            },
        )
        self._settled[call_id] = settlement
        self._crash_left.discard(call_id)
