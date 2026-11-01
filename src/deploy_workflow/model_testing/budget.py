"""Account spend and run caps. Only live runs are money; money is ``Decimal`` throughout."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from decimal import Context, Decimal, Inexact, InvalidOperation, localcontext

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


def account_spend(runs: Runs, account_id: Provider) -> Decimal:
    """Settled cost of live calls, plus the full reservation of any call whose cost is unknown."""
    total = Decimal(0)
    with localcontext(_EXACT):
        for meta, record in _checked(runs):
            if meta.mode != "live" or _provider(record.config_id) != account_id:
                continue
            if record.cost_status == "unknown" or record.settled_usd is None:
                total += record.reserved_usd
            else:
                total += record.settled_usd
    return total


def cap_for(config_id: str, runs: Runs) -> Decimal:
    account = ACCOUNTS[_provider(config_id)]
    spend = account_spend(runs, account.account_id)
    with localcontext(_EXACT):
        return max(Decimal(0), account.usable - spend)


def require_budget(config_id: str, runs: Runs, needed: Decimal) -> Decimal:
    if needed < 0:
        raise ValueError("needed must not be negative")
    holders = sorted(
        {
            meta.run_id
            for meta, record in _checked(runs)
            if meta.mode == "live"
            and record.config_id == config_id
            and record.cost_status == "unknown"
        }
    )
    if holders:
        raise UnknownCharge(
            f"{config_id}: unknown charge held by run(s) {', '.join(holders)}; "
            "configuration stopped until settled"
        )
    cap = cap_for(config_id, runs)
    if cap < needed:
        account = _provider(config_id)
        raise AccountExhausted(f"{config_id}: account {account} has {cap} usable, {needed} needed")
    return cap
