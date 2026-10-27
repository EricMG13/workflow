"""Registration is component evidence, never CP1B owner acceptance."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from deploy_vii.registry import dependencies, module_route, modules, step_chain, step_modules


def test_cp1b_has_exact_source_free_single_step():
    chain = step_chain("CP-1B")
    assert chain.cell == "cp1b" and chain.steps == ("earnings_delta",)
    assert chain.settling == "earnings_delta"
    for name in ("repairable", "prefilled", "projections", "pack_sources", "one_shot",
                 "pack_reads", "extract_tools", "part_submits"):
        assert not getattr(chain, name)
    assert step_modules()["earnings_delta"] == "CP-1B"
    assert module_route("CP-1B") == (
        "source_readiness", "source_context", "financials", "narrative", "readiness",
        "quality", "earnings_delta",
    )


def test_only_cp1b_table_ownership_changes():
    rows = json.loads((Path(__file__).parents[1] / "src/deploy_vii/methodology.json").read_text())
    cp1b = next(row for row in rows if row["module_id"] == "CP-1B")
    assert cp1b.pop("table_ids") == ["T1B.1", "T1B.2", "T1B.3"]
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == "0573968460da16ff13f4590b3f65edc4ebe06685c2e2840c8001b229747d86c6"
    assert next(m for m in modules() if m.module_id == "CP-1B").required == ("CP-0", "CP-1")
    assert dependencies(("CP-1B", "CP-5"))["CP-5"] == {"CP-0", "CP-1", "CP-1B"}
    assert step_chain("CP-5").steps == ("integrity_review",)
    assert step_chain("CP-2").steps == ("credit_synthesis",)


def test_shared_live_eligibility_preserves_all_existing_steps():
    from deploy_vii.registry import STEP_CHAINS, StepChain, shared_live_step_modules
    assert all(c.shared_live is (c.module_id != "CP-1B") for c in STEP_CHAINS)
    assert StepChain("CP-X", "x", ("x_step",)).shared_live is True
    eligible = shared_live_step_modules()
    assert list(eligible) == [
        "source_readiness", "source_context", "financials", "narrative", "readiness",
        "quality", "business_context", "credit_synthesis", "legal_covenants", "relative_value",
        "integrity_review", "committee_challenge",
    ]
    assert "earnings_delta" in step_modules() and "earnings_delta" not in eligible
    custom = (StepChain("CP-X", "x", ("offline_step",), shared_live=False),
              StepChain("CP-Y", "y", ("online_step",)))
    assert shared_live_step_modules(custom) == {"online_step": "CP-Y"}


@pytest.mark.parametrize("value", [None, 0, 1, "false", [], {}])
def test_shared_live_is_strict_bool(value):
    from deploy_vii.registry import StepChain
    with pytest.raises(ValueError, match="shared_live"):
        StepChain("CP-X", "x", ("x_step",), shared_live=value)


@pytest.mark.parametrize("reverse", [False, True])
def test_fresh_public_source_upstream_import_orders(reverse):
    names = ["deploy_workflow.tools.source", "deploy_workflow.tools.upstream"]
    if reverse:
        names.reverse()
    script = "import importlib; " + "; ".join(f"importlib.import_module({n!r})" for n in names)
    child = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert child.returncode == 0, child.stderr
    assert not child.stdout


def test_live_schema_totality_remains_strict_and_offline_keys_are_guarded():
    from deploy_vii.live.submission import STEPS, step_definitions
    from deploy_vii.registry import shared_live_step_modules
    schemas = {key: value.schema for key, value in STEPS.items()}
    assert list(STEPS) == list(shared_live_step_modules())
    assert "earnings_delta" not in STEPS and STEPS.get("earnings_delta") is None
    assert isinstance(STEPS, dict)
    assert step_definitions(schemas) == STEPS
    with pytest.raises(ValueError, match="no model-facing schema for financials"):
        step_definitions({k: v for k, v in schemas.items() if k != "financials"})
    for extra in ("unknown_step", "earnings_delta"):
        with pytest.raises(ValueError):
            step_definitions({**schemas, extra: schemas["financials"]})
    with pytest.raises(ValueError, match="offline-only"):
        _ = STEPS["earnings_delta"]
    with pytest.raises(KeyError):
        _ = STEPS["unknown_step"]


@pytest.mark.parametrize("kind", [None, "submit-only", "pack"])
def test_offline_tool_schema_requests_refuse_explicitly(kind):
    from deploy_vii.live.tools import submit_spec, tool_specs
    with pytest.raises(ValueError, match="offline-only"):
        submit_spec("earnings_delta")
    with pytest.raises(ValueError, match="offline-only"):
        tool_specs("earnings_delta", kind)
