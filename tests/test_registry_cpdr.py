"""O7b-1c S4: the CP-DR registry row, read against the key.

Answer key: `cases/cpdr-research-owner/expected.json#registry_after_o7b1` (frozen; read at test
time, never edited). Surface: `deploy_vii.registry` over `src/deploy_vii/methodology.json`.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import registry
from deploy_vii.contracts import PATHWAY_MODULES, PathwayId

ROOT = Path(__file__).resolve().parents[1]
KEY: dict[str, Any] = json.loads(
    (ROOT / "cases/cpdr-research-owner/expected.json").read_text(encoding="utf-8")
)["registry_after_o7b1"]
ROW: dict[str, Any] = KEY["CP-DR"]
PRESETS = sorted(PATHWAY_MODULES)


def _row() -> registry.Responsibility:
    return next(m for m in registry.modules() if m.module_id == "CP-DR")


def test_the_cpdr_row_is_the_keys_row() -> None:
    row = _row()
    assert list(row.required) == ROW["required"]
    assert list(row.table_ids) == ROW["table_ids"]
    assert ROW["purpose_contains"] in row.purpose


def test_methodology_registers_tdr4_to_6() -> None:
    """Row 20: `methodology.json` registers TDR.1-6 for CP-DR, in the key's order, and every table
    the peers key composes is among them (D0b registered them; D1b's bindings render them)."""
    wanted = ["TDR.1", "TDR.2", "TDR.3", "TDR.4", "TDR.5", "TDR.6"]
    assert ROW["table_ids"] == wanted
    assert list(_row().table_ids) == ROW["table_ids"]
    peers: dict[str, Any] = json.loads(
        (ROOT / "cases/cpdr-peers-owner/expected.json").read_text(encoding="utf-8")
    )
    assert {t for t in peers["tables"] if t.startswith("TDR.")} <= set(_row().table_ids)


def test_the_cpdr_row_sits_directly_before_cp1c() -> None:
    ids = [m.module_id for m in registry.modules()]
    assert ids.index("CP-DR") + 1 == ids.index("CP-1C")


def test_the_plan_of_cp1_and_cpdr_is_the_keys_order() -> None:
    assert list(registry.plan(("CP-1", "CP-DR"))) == KEY["plan_order_for_requested_CP-1_CP-DR"]


@pytest.mark.parametrize("pathway", PRESETS)
def test_a_preset_with_cpdr_orders_it_after_cp1_before_cp1c_and_cp2(pathway: PathwayId) -> None:
    order = registry.plan((*PATHWAY_MODULES[pathway], "CP-DR"))
    assert order.index("CP-1") < order.index("CP-DR")
    for later in ("CP-1C", "CP-2"):
        if later in order:
            assert order.index("CP-DR") < order.index(later), later


@pytest.mark.parametrize("pathway", PRESETS)
def test_a_preset_alone_excludes_cpdr(pathway: PathwayId) -> None:
    assert "CP-DR" not in PATHWAY_MODULES[pathway]
    assert "CP-DR" not in registry.plan(PATHWAY_MODULES[pathway])


def test_the_presets_exercise_both_later_modules() -> None:
    """The order check above is not vacuous: some preset holds CP-1C and some holds CP-2."""
    held = {m for modules in PATHWAY_MODULES.values() for m in modules}
    assert {"CP-1C", "CP-2"} <= held


def test_no_module_lists_cpdr_as_required_or_optional() -> None:
    for module in registry.modules():
        assert "CP-DR" not in module.required, module.module_id
        assert "CP-DR" not in module.optional, module.module_id


def test_cp5_depends_on_cpdr_when_both_are_selected() -> None:
    graph = registry.dependencies(("CP-1", "CP-DR", "CP-5"))
    assert "CP-DR" in graph["CP-5"]
    assert graph["CP-DR"] == set(ROW["required"])
