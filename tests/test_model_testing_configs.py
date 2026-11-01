from decimal import Decimal
from pathlib import Path

from deploy_workflow.model_testing.configs import (
    ACCOUNTS,
    CASES,
    CONFIGS,
    OPUS_PATHWAYS,
    PILOT_PATHWAY,
)


def test_usable_caps() -> None:
    assert {a: ACCOUNTS[a].usable for a in ACCOUNTS} == {
        "openai": Decimal("117.00"),
        "anthropic": Decimal("135.00"),
        "openrouter": Decimal("18.00"),
    }


def test_configs_match_ruling() -> None:
    assert set(CONFIGS) == {"sol-medium", "sol-high", "opus-medium", "deepseek-max"}
    assert CONFIGS["opus-medium"].model == "claude-opus-5-5"
    assert CONFIGS["opus-medium"].effort == "medium"
    assert CONFIGS["deepseek-max"].model == "deepseek/deepseek-v4.1-flash-1017"
    assert {c for c, m in CONFIGS.items() if "repair" in m.roles} == {
        "sol-medium",
        "deepseek-max",
    }


def test_configs_agree_with_orchestrator() -> None:
    from deploy_workflow.model.turn import CONFIG_PROVIDERS, ModelSpec

    assert {c: m.provider for c, m in CONFIGS.items()} == dict(CONFIG_PROVIDERS)
    for m in CONFIGS.values():
        ModelSpec(m.config_id, m.provider, m.model, m.effort)


def test_cases_cover_every_preset() -> None:
    from deploy_vii.contracts import PATHWAY_MODULES

    assert set(CASES) == set(PATHWAY_MODULES)
    assert all((Path("cases/goldens") / d / "module_golden.json").is_file() for d in CASES.values())


def test_opus_pathways_exclude_distressed() -> None:
    assert "distressed_restructuring" not in OPUS_PATHWAYS
    assert OPUS_PATHWAYS[0] == PILOT_PATHWAY
