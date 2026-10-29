"""The shared Stage 2 hostile-text classes (`tests/defect_classes.py`) over the modules in the lane.

- Round 1 Q5: every step schema of `OWNER_SPECS` and every owner module's `SCHEMAS` row raises only
  `ValueError` subclasses on hostile stored text.
- Round 3 item 2: every free-text field of the positive payload of a module whose run is fast to
  reach is fed `MODEL_TEXT_HOSTILE`, through the public `OwnerWorkflow` over a real `Execution`.
  CP-0 is driven here; CP-1A and CP-2 sit behind CP-1's slow financial stages (S1a, 11 to 26
  minutes) and join when a connection test can reach them cheaply. A module that fails is fixed in
  its own task, not here.
"""

import importlib
import pkgutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import defect_classes as dc
import pytest
import s1a_runs
from pydantic import BaseModel

from deploy_vii.contracts import Contract
from deploy_vii.live.submission import STEPS
from deploy_vii.preparation import PreparedPack
from deploy_workflow import owners
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerWorkflow


def _schemas() -> dict[str, type[BaseModel]]:
    """LEAD's Q5 probe set, registered or not: every `OWNER_SPECS` step schema, every live `STEPS`
    schema, every owner module's `SCHEMAS` row, and every `*Submission` contract that an owner
    module defines (the schemas its Stage 2 `SCHEMAS` row will name)."""
    found: dict[str, type[BaseModel]] = {}
    for module_id, spec in OWNER_SPECS.items():
        for step in spec.steps:
            found[f"{module_id}.{step.step_id}"] = step.schema
    for step_id, definition in STEPS.items():
        found.setdefault(f"STEPS.{step_id}", definition.schema)
    for info in pkgutil.iter_modules(owners.__path__):
        module = importlib.import_module(f"deploy_workflow.owners.{info.name}")
        for step_id, schema in dict(getattr(module, "SCHEMAS", {}) or {}).items():
            found[f"owners.{info.name}.{step_id}"] = schema
        for name, value in vars(module).items():
            if (
                isinstance(value, type)
                and issubclass(value, Contract)
                and name.endswith("Submission")
                and value.__module__ == module.__name__
            ):
                found.setdefault(f"owners.{info.name}.{name}", value)
    return found


SCHEMAS = _schemas()


def test_registered_schemas_are_found() -> None:
    assert {"CP-0.source_readiness", "CP-1A.business_context", "CP-2.credit_synthesis"} <= set(
        SCHEMAS
    )
    # the live STEPS schemas of CP-3 to CP-6 and the unregistered Stage 2 Submission classes
    assert {n for n in SCHEMAS if n.startswith("STEPS.")}
    assert any(n.startswith("owners.cp2a") for n in SCHEMAS)
    assert len({id(schema) for schema in SCHEMAS.values()}) >= 19


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_hostile_stored_text_raises_only_value_errors(name: str) -> None:
    dc.assert_hostile_refused(SCHEMAS[name])


class _Cp0Run:
    """CP-0 over a real store: each submit first reads the pages the positive payload cites (a
    refused attempt re-activates the step on a new binding, which needs its reads again)."""

    def __init__(self, workflow: OwnerWorkflow, positive: str) -> None:
        self._workflow = workflow
        self._positive = positive

    def submit_review(self, payload: str) -> Mapping[str, Any]:
        s1a_runs.read_cited(self._workflow, self._positive)
        outcome: Mapping[str, Any] = self._workflow.submit_review(payload)
        return outcome


def _cp0_fresh(tmp: Path, positive: str, pack: PreparedPack) -> Callable[[], dc.ReviewRun]:
    counter = iter(range(10_000))

    def fresh() -> dc.ReviewRun:
        root = tmp / str(next(counter))
        root.mkdir()
        workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
        return _Cp0Run(workflow, positive)

    return fresh


# CP-0's verbatim paths (round 5 item 10) and the sink of each. Every one is stored as plain text
# (`Fact.text: str | None`, `Module.limitations: tuple[str, ...]`, `Claim.limitation: str | None`)
# by `readiness.build_readiness` and is never built as `RunText` or `Claim.text`. Every other free
# text path of the payload, including all citation quotes and locators, must journal an issue.
CP0_VERBATIM: Mapping[tuple[str | int, ...], str] = {
    ("objective",): "Fact.text (T1 run.objective)",
    ("reporting_period",): "Fact.text (T1 run.reporting_period)",
    ("sources", "*", "document_family"): "Fact.text (P3 family)",
    ("sources", "*", "entity"): "Fact.text (P3 entity)",
    ("sources", "*", "period"): "Fact.text (P3 period)",
    ("sources", "*", "version_relationship"): "Fact.text (P3 version_relationship)",
    ("sources", "*", "limitations", "*"): "Module.limitations (str) and Fact.text (T8 limits)",
    ("consumers", "*", "evidence_demand"): "Fact.text (T4 demand)",
    ("consumers", "*", "rationale"): "Fact.text (T4 rationale)",
    ("consumers", "*", "limitations", "*"): "Module.limitations (str) and Fact.text (T8 limits)",
    ("consumers", "*", "missing_source"): "ConsumerReadiness.missing_source (str | None): checked"
    " by the absence-claim rule (`readiness.py:321`), required when CONDITIONAL, and read nowhere else",
    ("analysis", "*", "limitation"): "Claim.limitation (str | None; Claim.text is not this)",
}


def test_cp0_model_text_is_journaled_except_on_its_verbatim_paths(tmp_path: Path) -> None:
    pack = s1a_runs.make_pack("positive")
    positive = s1a_runs.literal("positive", "readiness_review", pack)
    schema = OWNER_SPECS["CP-0"].steps[0].schema
    assert dc.free_text_paths(positive, schema), "CP-0 has free-text fields"
    failures = dc.model_text_failures(
        schema,
        positive,
        _cp0_fresh(tmp_path, positive, pack),
        verbatim=frozenset(CP0_VERBATIM),
        fill_absent=True,  # round 5 item 10 L2: gaps and consumers the positive leaves null
    )
    assert failures == []
