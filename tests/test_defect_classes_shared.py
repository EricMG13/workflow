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

from deploy_vii.preparation import PreparedPack
from deploy_workflow import owners
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerWorkflow


def _schemas() -> dict[str, type[BaseModel]]:
    found: dict[str, type[BaseModel]] = {}
    for module_id, spec in OWNER_SPECS.items():
        for step in spec.steps:
            found[f"{module_id}.{step.step_id}"] = step.schema
    for info in pkgutil.iter_modules(owners.__path__):
        module = importlib.import_module(f"deploy_workflow.owners.{info.name}")
        for step_id, schema in dict(getattr(module, "SCHEMAS", {}) or {}).items():
            found[f"owners.{info.name}.{step_id}"] = schema
    return found


SCHEMAS = _schemas()


def test_registered_schemas_are_found() -> None:
    assert {"CP-0.source_readiness", "CP-1A.business_context", "CP-2.credit_synthesis"} <= set(
        SCHEMAS
    )


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


def test_cp0_model_text_never_raises_or_wedges_the_run(tmp_path: Path) -> None:
    pack = s1a_runs.make_pack("positive")
    positive = s1a_runs.literal("positive", "readiness_review", pack)
    schema = OWNER_SPECS["CP-0"].steps[0].schema
    assert dc.free_text_paths(positive, schema), "CP-0 has free-text fields"
    # CP-0 takes its objective, period and similar fields verbatim (no build over them), so a
    # bracket there is accepted: `require_issue` is off. Citation fields are still refused.
    failures = dc.model_text_failures(
        schema, positive, _cp0_fresh(tmp_path, positive, pack), require_issue=False
    )
    assert failures == []


class _Cp1ContextRun:
    """CP-1's first step over a real store, after a valid CP-0: each submit repeats the reads and
    the two searches the literal `source_context` needs."""

    def __init__(self, workflow: OwnerWorkflow, positive: str) -> None:
        self._workflow = workflow
        self._positive = positive

    def submit_review(self, payload: str) -> Mapping[str, Any]:
        s1a_runs.read_cited(self._workflow, self._positive)
        s1a_runs.search(self._workflow, "financial", "subsequent")
        s1a_runs.search(self._workflow, "business", "acquisition")
        outcome: Mapping[str, Any] = self._workflow.submit_review(payload)
        return outcome


def test_cp1_source_context_model_text_never_raises_or_wedges_the_run(tmp_path: Path) -> None:
    pack = s1a_runs.make_pack("positive")
    positive = s1a_runs.literal("positive", "cp1_source_context", pack)
    schema = OWNER_SPECS["CP-1"].steps[0].schema
    assert dc.free_text_paths(positive, schema), "source_context has free-text fields"
    # One workflow with CP-0 settled and CP-1 untouched; each case forks it (before any call).
    template, _ = s1a_runs.start("positive", tmp_path / "template")
    s1a_runs.drive_cp0(template, pack, "positive")
    counter = iter(range(10_000))

    def fresh() -> dc.ReviewRun:
        fork = s1a_runs.clone_workflow(template, tmp_path / str(next(counter)))
        return _Cp1ContextRun(fork, positive)

    failures = dc.model_text_failures(schema, positive, fresh, require_issue=False)
    assert failures == []
