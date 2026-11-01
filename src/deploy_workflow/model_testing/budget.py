"""Account spend and run caps. Only live runs are money; money is ``Decimal`` throughout."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing.configs import ACCOUNTS, CONFIGS, Provider
from deploy_workflow.model_testing.records import RunMeta

Runs = Sequence[tuple[RunMeta, Sequence[CallRecord]]]


class AccountExhausted(RuntimeError):
    """An account's usable credit cannot cover the amount needed."""


def _provider(config_id: str) -> Provider:
    config = CONFIGS.get(config_id)
    if config is None:
        raise KeyError(f"unknown config_id {config_id}")
    return config.provider


def account_spend(runs: Runs, account_id: Provider) -> Decimal:
    """Settled cost of live calls, plus the full reservation of any call whose cost is unknown."""
    total = Decimal(0)
    for meta, records in runs:
        if meta.mode != "live":
            continue
        for record in records:
            if _provider(record.config_id) != account_id:
                continue
            if record.cost_status == "unknown" or record.settled_usd is None:
                total += record.reserved_usd
            else:
                total += record.settled_usd
    return total


def cap_for(config_id: str, runs: Runs) -> Decimal:
    account = ACCOUNTS[_provider(config_id)]
    return max(Decimal(0), account.usable - account_spend(runs, account.account_id))


def require_budget(config_id: str, runs: Runs, needed: Decimal) -> Decimal:
    if needed < 0:
        raise ValueError("needed must not be negative")
    cap = cap_for(config_id, runs)
    if cap < needed:
        account = _provider(config_id)
        raise AccountExhausted(f"{config_id}: account {account} has {cap} usable, {needed} needed")
    return cap
