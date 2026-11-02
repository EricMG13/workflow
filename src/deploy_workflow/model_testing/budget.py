"""Account spend and run caps. Only live runs are money; money is ``Decimal`` throughout."""

from __future__ import annotations

import datetime
from collections.abc import Iterator, Sequence
from decimal import Context, Decimal, Inexact, InvalidOperation, localcontext
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator

from deploy_vii.contracts import Contract
from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing.configs import ACCOUNTS, CONFIGS, Provider
from deploy_workflow.model_testing.records import RunMeta

Runs = Sequence[tuple[RunMeta, Sequence[CallRecord]]]

# Money sums are exact (as in model/budget.py): a sum wider than the context raises.
_EXACT = Context(prec=120, traps=[InvalidOperation, Inexact])


class AccountExhausted(RuntimeError):
    """An account's usable credit cannot cover the amount needed."""


class UnknownCharge(AccountExhausted):
    """A live call's charge is unknown: the configuration stays stopped (spec 7.2)."""


class Settlement(Contract):
    """The user's statement of what an unknown live charge really cost (MANAGER ruling
    2026-11-01). The framework reads it and never writes it."""

    run_id: str = Field(min_length=1)
    call_index: int
    settled_usd: Decimal
    by: str = Field(min_length=1)
    date: str
    source: str = Field(min_length=1)

    @field_validator("date")
    @classmethod
    def _iso_date(cls, value: str) -> str:
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise ValueError("date must be an ISO date (YYYY-MM-DD)") from None
        return value


class _SettlementFile(Contract):
    schema_version: Literal["charge-settlement/1"]
    entries: tuple[Settlement, ...]


def load_settlements(path: Path) -> tuple[Settlement, ...]:
    """The entries of a user-filled settlements file; no file means no settlements."""
    if not path.is_file():
        return ()
    try:
        return _SettlementFile.model_validate_json(path.read_bytes()).entries
    except ValidationError as error:
        shown = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}"
            for e in error.errors(include_input=False, include_url=False, include_context=False)[:5]
        )
        raise ValueError(f"{path.name}: invalid: {shown}") from None


def _provider(config_id: str) -> Provider:
    config = CONFIGS.get(config_id)
    if config is None:
        raise KeyError(f"unknown config_id {config_id}")
    return config.provider


def _where(record: CallRecord) -> str:
    return (
        f"run {record.run_id} module {record.module_id} step {record.step_id} "
        f"call {record.call_index}"
    )


def _checked(runs: Runs) -> Iterator[tuple[RunMeta, CallRecord]]:
    """Yield every record after refusing inconsistent or non-money values."""
    for meta, records in runs:
        for record in records:
            if record.config_id != meta.config_id:
                raise ValueError(f"{_where(record)}: config_id differs from its run")
            if record.provider != _provider(record.config_id):
                raise ValueError(f"{_where(record)}: provider does not match its config_id")
            for amount in (record.reserved_usd, record.settled_usd):
                if amount is not None and (not amount.is_finite() or amount < 0):
                    raise ValueError(f"{_where(record)}: money must be finite and not negative")
            yield meta, record


Key = tuple[str, int]


def _settled_amounts(
    rows: Sequence[tuple[RunMeta, CallRecord]], settlements: Sequence[Settlement]
) -> dict[Key, Decimal]:
    """The settled amount per (run_id, call_index), after refusing a settlement that is a
    duplicate, matches no record or more than one, targets a record whose charge is known, or
    carries a negative or non-finite amount."""
    records: dict[Key, list[CallRecord]] = {}
    for _, record in rows:
        records.setdefault((record.run_id, record.call_index), []).append(record)
    found: dict[Key, Decimal] = {}
    for item in settlements:
        key = (item.run_id, item.call_index)
        where = f"settlement for run {item.run_id} call {item.call_index}"
        if key in found:
            raise ValueError(f"{where}: duplicate settlement")
        if not item.settled_usd.is_finite() or item.settled_usd < 0:
            raise ValueError(f"{where}: settled_usd must be finite and not negative")
        matched = records.get(key, [])
        if not matched:
            raise ValueError(f"{where}: matches no record")
        if len(matched) > 1:
            raise ValueError(f"{where}: matches {len(matched)} records")
        if matched[0].cost_status != "unknown":
            raise ValueError(f"{where}: the record's charge is not unknown")
        found[key] = item.settled_usd
    return found


def account_spend(
    runs: Runs, account_id: Provider, settlements: Sequence[Settlement] = ()
) -> Decimal:
    """Settled cost of live calls, plus the full reservation of any call whose cost is unknown
    and not settled by a user settlement (whose amount counts instead)."""
    total = Decimal(0)
    rows = list(_checked(runs))
    settled = _settled_amounts(rows, settlements)
    with localcontext(_EXACT):
        for meta, record in rows:
            if meta.mode != "live" or _provider(record.config_id) != account_id:
                continue
            key = (record.run_id, record.call_index)
            if record.cost_status == "unknown" and key in settled:
                total += settled[key]
            elif record.cost_status == "unknown" or record.settled_usd is None:
                total += record.reserved_usd
            else:
                total += record.settled_usd
    return total


def cap_for(config_id: str, runs: Runs, settlements: Sequence[Settlement] = ()) -> Decimal:
    account = ACCOUNTS[_provider(config_id)]
    spend = account_spend(runs, account.account_id, settlements)
    with localcontext(_EXACT):
        return max(Decimal(0), account.usable - spend)


def require_budget(
    config_id: str, runs: Runs, needed: Decimal, settlements: Sequence[Settlement] = ()
) -> Decimal:
    if needed < 0:
        raise ValueError("needed must not be negative")
    rows = list(_checked(runs))
    settled = _settled_amounts(rows, settlements)
    holders = sorted(
        {
            meta.run_id
            for meta, record in rows
            if meta.mode == "live"
            and record.config_id == config_id
            and record.cost_status == "unknown"
            and (record.run_id, record.call_index) not in settled
        }
    )
    if holders:
        raise UnknownCharge(
            f"{config_id}: unknown charge held by run(s) {', '.join(holders)}; "
            "configuration stopped until settled"
        )
    cap = cap_for(config_id, runs, settlements)
    if cap < needed:
        account = _provider(config_id)
        raise AccountExhausted(f"{config_id}: account {account} has {cap} usable, {needed} needed")
    return cap
