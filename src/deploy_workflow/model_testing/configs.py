"""Model configurations, provider accounts and case table (spec §7.1-7.3)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

from deploy_vii.contracts import PathwayId

Provider = Literal["openai", "anthropic", "openrouter"]
Role = Literal["repair", "comparison"]


@dataclass(frozen=True)
class ModelConfig:
    config_id: str
    provider: Provider
    model: str
    effort: str
    roles: frozenset[Role]


@dataclass(frozen=True)
class Account:
    account_id: Provider
    credit: Decimal
    reserve: Decimal = Decimal("0.10")

    @property
    def usable(self) -> Decimal:
        return self.credit * (1 - self.reserve)


CONFIGS: Mapping[str, ModelConfig] = MappingProxyType(
    {
        "sol-medium": ModelConfig(
            "sol-medium", "openai", "gpt-6.1-sol", "medium", frozenset({"repair", "comparison"})
        ),
        "sol-high": ModelConfig(
            "sol-high", "openai", "gpt-6.1-sol", "high", frozenset({"comparison"})
        ),
        "opus-medium": ModelConfig(
            "opus-medium", "anthropic", "claude-opus-5-5", "medium", frozenset({"comparison"})
        ),
        "deepseek-max": ModelConfig(
            "deepseek-max",
            "openrouter",
            "deepseek/deepseek-v4.1-flash-1017",
            "max",
            frozenset({"repair", "comparison"}),
        ),
    }
)

ACCOUNTS: Mapping[Provider, Account] = MappingProxyType(
    {
        "openai": Account("openai", Decimal(130)),
        "anthropic": Account("anthropic", Decimal(150)),
        "openrouter": Account("openrouter", Decimal(20)),
    }
)

CASES: Mapping[PathwayId, str] = MappingProxyType(
    {
        "credit_snapshot": "tdg-credit-snapshot",
        "earnings_update": "shc-earnings-update",
        "relative_value": "bgs-relative-value",
        "covenant_refinancing": "lth-covenant-refinancing",
        "distressed_restructuring": "ihrt-distressed-restructuring",
        "portfolio_decision": "natl-portfolio-decision",
    }
)

PILOT_PATHWAY: PathwayId = "earnings_update"

OPUS_PATHWAYS: tuple[PathwayId, ...] = (
    "earnings_update",
    "portfolio_decision",
    "credit_snapshot",
    "covenant_refinancing",
    "relative_value",
)
