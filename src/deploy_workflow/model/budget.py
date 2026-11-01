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
cut stream); the hold itself stays counted, and the stop lifts only after that retry settles
with a number (below). An overrun is never retryable.

The stop for an unknown charge ``c`` lifts only when the retry naming it (``retry_of == c``) has
settled with a number (not unknown, not an overrun). A retry is used once it is reserved. A retry
is refused while any overrun, any other unresolved unknown or any crash-left marker stands. A
crash-left id is cleared only by ``settle(id, actual)``, never by ``release``. A failed marker
write sets a sticky stop.
"""

from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Context, Decimal, Inexact, InvalidOperation
from pathlib import Path

from deploy_workflow.model.pricing import money_text, price_of, refusal_values

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
# Money sums must be exact: a sum wider than the context raises instead of rounding.
_EXACT = Context(prec=120, traps=[InvalidOperation, Inexact])
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


def _add(left: Decimal, right: Decimal) -> Decimal:
    """Exact sum; a sum too wide for the context is a BudgetError, never a rounded number."""
    try:
        return _EXACT.add(left, right)
    except Inexact:
        raise BudgetError("money sum not exact") from None


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
    _fsync_dir(path.parent)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _make_dirs(target: Path) -> None:
    """mkdir -p, then fsync the parent of every directory this call created."""
    missing: list[Path] = []
    probe = target
    while not probe.exists():
        missing.append(probe)
        probe = probe.parent
    for directory in reversed(missing):
        directory.mkdir()
        _fsync_dir(directory.parent)


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
        # ponytail: single-process runner. Add an exclusive flock on owner-run-audit/ if a second
        # process can share an Execution dir (two Budgets over one dir are not coordinated).
        self._lock = threading.Lock()
        self._holds: dict[str, _Hold] = {}
        self._settled: dict[str, _Settlement] = {}
        self._crash_left: set[str] = set()
        self._faulted = False
        _make_dirs(self._dir)
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
    def stop_reason(self) -> str | None:
        """Why the run is stopped (an unknown charge, an overrun, a crash-left hold), or None."""
        with self._lock:
            return self._stops()

    @property
    def settled_calls(self) -> tuple[str, ...]:
        """The sorted ids of the reservations settled as sent: a settled marker whose status is
        not ``released`` (a released hold was never sent)."""
        with self._lock:
            return tuple(sorted(c for c, s in self._settled.items() if s.status != "released"))

    @property
    def unsettled(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(c for c in self._holds if c not in self._settled))

    def _reserved(self) -> Decimal:
        return self._sum(h.usd for c, h in self._holds.items() if c not in self._settled)

    def _spent(self) -> Decimal:
        return self._sum(s.usd for s in self._settled.values())

    @staticmethod
    def _sum(values: Iterable[Decimal]) -> Decimal:
        total = Decimal(0)
        for value in values:
            total = _add(total, value)
        return total

    def _retried(self) -> set[str]:
        return {h.retry_of for h in self._holds.values() if h.retry_of is not None}

    def _resolved(self) -> set[str]:
        """Unknown charges whose retry settled with a number."""
        return {
            h.retry_of
            for c, h in self._holds.items()
            if h.retry_of is not None
            and c in self._settled
            and self._settled[c].status == "settled"
        }

    def _stops(self, *, except_unknown: str | None = None) -> str | None:
        """Why the run is stopped, or None."""
        if self._faulted:
            return "a marker write failed"
        if self._crash_left:
            return "a reservation left unsettled by a crash"
        resolved = self._resolved()
        for call_id, settlement in self._settled.items():
            if settlement.status == "overrun":
                return f"{call_id!r} overran its reservation"
            if (
                settlement.status == "unknown"
                and call_id not in resolved
                and call_id != except_unknown
            ):
                return f"{call_id!r} has an unknown charge"
        return None

    # -- operations -------------------------------------------------------------------

    def reserve(
        self, call_id: str, usd: Decimal, retry_of: str | None = None, *, config_id: str
    ) -> None:
        call_id = _call_id(call_id)
        amount = _decimal("usd", usd)
        if not isinstance(config_id, str) or not config_id:
            raise BudgetError("config_id must be a non-empty string")
        price_of(config_id)  # NoPrice for a configuration the table does not cover
        with self._lock:
            if retry_of is None:
                reason = self._stops()
                if reason is not None:
                    raise RunStopped(f"the run is stopped: {reason}")
            else:
                self._check_retry(_call_id(retry_of))
            committed = _add(_add(self._reserved(), self._spent()), amount)
            if committed > self._cap:
                raise BudgetExhausted(
                    f"reserving {money_text(amount)} passes the cap {money_text(self._cap)}"
                )
            self._write(
                self._dir / call_id,
                {"usd": str(amount), "config_id": config_id, "retry_of": retry_of},
            )
            self._holds[call_id] = _Hold(amount, config_id, retry_of)

    def _check_retry(self, retry_of: str) -> None:
        if self._retried():
            raise RetryUsed("the run's one retry was already taken")
        reason = self._stops(except_unknown=retry_of)
        if reason is not None:
            raise RunStopped(f"a retry is refused: {reason}")
        settlement = self._settled.get(retry_of)
        if settlement is None or settlement.status != "unknown" or not settlement.retryable:
            raise RunStopped(f"{retry_of!r} is not a retryable unknown-charge hold")

    def _write(self, path: Path, payload: dict[str, object]) -> None:
        """A failed write after the create-once file may exist leaves unknown state: stop."""
        try:
            _write_once(path, payload)
        except DuplicateCall:
            raise
        except OSError:
            self._faulted = True
            raise

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
            if call_id in self._crash_left:
                raise RunStopped(
                    f"{call_id!r} may have been sent; settle it with its actual charge"
                )
            self._record(call_id, _Settlement("released", Decimal(0), False))

    def _open_hold(self, call_id: str) -> _Hold:
        hold = self._holds.get(call_id)
        if hold is None:
            raise BudgetError(f"no reservation for {call_id!r}")
        if call_id in self._settled:
            raise DuplicateCall(f"{call_id!r} is already settled")
        return hold

    def _record(self, call_id: str, settlement: _Settlement) -> None:
        self._write(
            self._dir / (call_id + _SETTLED),
            {
                "status": settlement.status,
                "usd": str(settlement.usd),
                "retryable": settlement.retryable,
            },
        )
        self._settled[call_id] = settlement
        self._crash_left.discard(call_id)
