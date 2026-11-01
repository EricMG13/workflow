"""Pathway presets against the owner walk (Part B O1; user ruling B1).

Task 1 (G1a): CP-5's fan-in excludes CP-MODEL, so CP-MODEL is a stop in the walk and an
analytical module may follow it. Task 3 (G1c): CP-1B is an owner-only core, so `earnings_update`
is admitted too. The other presets are asserted in Task 4.
"""

import datetime as dt
from pathlib import Path

import pytest

from deploy_vii.contracts import PATHWAY_MODULES, Run
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import dependencies, edge_rule, plan
from deploy_workflow import owner_workflow as ow

PLANS = {
    "earnings_update": ("CP-0", "CP-1", "CP-1B", "CP-MODEL", "CP-1D", "CP-5"),
    "relative_value": (
        "CP-0",
        "CP-1",
        "CP-1A",
        "CP-3D",
        "CP-1C",
        "CP-MODEL",
        "CP-2",
        "CP-2D",
        "CP-3C",
        "CP-3",
        "CP-5",
    ),
    "covenant_refinancing": (
        "CP-0",
        "CP-1",
        "CP-1A",
        "CP-2",
        "CP-4",
        "CP-MODEL",
        "CP-2D",
        "CP-3C",
        "CP-5",
    ),
}


def test_cp5_fan_in_excludes_cp_model() -> None:
    assert dependencies(("CP-1", "CP-MODEL", "CP-5"))["CP-5"] == {"CP-0", "CP-1"}
    with pytest.raises(ValueError, match="No dependency edge"):
        edge_rule("CP-5", "CP-MODEL")
    assert dependencies(("CP-1B", "CP-5"))["CP-5"] == {"CP-0", "CP-1", "CP-1B"}


@pytest.mark.parametrize("pathway", sorted(PLANS))
def test_check_specs_admits_earnings_relative_value_and_covenant_refinancing(
    pathway: str, tmp_path: Path
) -> None:
    run = Run(
        run_id="r1",
        issuer_id="i1",
        issuer_name="I",
        as_of=dt.date(2026, 1, 1),
        case_kind="synthetic",
        pathway=pathway,  # type: ignore[arg-type]
    )
    pack = PreparedPack(run=run, sources=())
    planned = ow._check_specs(pack, ow.OWNER_SPECS, tmp_path / "pub", tmp_path / "ex")
    assert planned == PLANS[pathway]


BASELINE = {
    "credit_snapshot": (
        "CP-0",
        "CP-1",
        "CP-1A",
        "CP-2",
        "CP-4",
        "CP-MODEL",
        "CP-3",
        "CP-5",
        "CP-6",
    ),
    **PLANS,
    "distressed_restructuring": (
        "CP-0",
        "CP-1",
        "CP-1A",
        "CP-2",
        "CP-2A",
        "CP-4",
        "CP-2G",
        "CP-2H",
        "CP-4C",
        "CP-5",
    ),
    "portfolio_decision": (
        "CP-0",
        "CP-1",
        "CP-1A",
        "CP-2",
        "CP-MODEL",
        "CP-3",
        "CP-5",
        "CP-6",
        "CP-8",
    ),
}


@pytest.mark.parametrize("pathway", sorted(PATHWAY_MODULES))
def test_check_specs_passes_for_all_six_presets(pathway: str, tmp_path: Path) -> None:
    run = Run(
        run_id="r1",
        issuer_id="i1",
        issuer_name="I",
        as_of=dt.date(2026, 1, 1),
        case_kind="synthetic",
        pathway=pathway,  # type: ignore[arg-type]
    )
    pack = PreparedPack(run=run, sources=())
    planned = ow._check_specs(
        pack, ow.OWNER_SPECS, tmp_path / f"pub-{pathway}", tmp_path / f"ex-{pathway}"
    )
    assert planned == BASELINE[pathway] == plan(run.requested_modules)
    for module_id in planned:
        assert module_id in ow.OWNER_SPECS
        if module_id == "CP-MODEL":  # the deterministic stop: no analytical probe
            assert ow.OWNER_SPECS[module_id].kind == "deterministic"
        else:
            assert module_id in ow.SUPPORTED_ANALYTICAL
            assert module_id in ow._PROBES
