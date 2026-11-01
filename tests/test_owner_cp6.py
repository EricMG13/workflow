"""CP-6 committee challenge in the owner walk (Part B O1, Task 2, G1b).

The registration tests are fast. The two run tests drive the closed R6 fixture of
`cases/cp3-cp6-owner` (CP-0, CP-1, CP-1A, CP-2, CP-3, CP-5, CP-6) and need a real CP-1
promotion (11-26 minutes), so they run only under `RUN_PROMOTION=1`. A failure there is a
finding on the frozen oracle, never patched here.
"""

import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import cp3_cp6_runs as runs
import pytest

from deploy_vii.contracts import Run
from deploy_vii.execution import Execution
from deploy_vii.live.context import module_context
from deploy_vii.preparation import PreparedPack
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.owners import cp6
from deploy_workflow.workflow import WorkflowError

STEP = "committee_challenge"
CASE = "positive"

promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred"
)


def test_cp6_spec_registered() -> None:
    spec = owner.OWNER_SPECS["CP-6"]
    assert spec.entry == "model_payload" and spec.kind == "analytical" and spec.publish is None
    assert [s.step_id for s in spec.steps] == [STEP]
    assert spec.steps[0].inputs == "module_context" and not spec.steps[0].sources
    assert "CP-6" in owner.SUPPORTED_ANALYTICAL
    assert owner._QUALIFICATION["CP-6"] is cp6.QUALIFICATION
    assert owner._PROBES["CP-6"] is cp6.probe
    assert owner._ENTRY_VALIDATORS["CP-6"] is cp6.ENTRY_VALIDATOR
    assert owner._VIEWS[STEP] is cp6.view
    assert "CP-6" not in owner._CORES  # live-contract: no owner_core dispatch
    owner._check_steps("CP-6", spec)


PLANS = {
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


@pytest.mark.parametrize("pathway", sorted(PLANS))
def test_check_specs_admits_credit_snapshot_and_portfolio_decision(
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
    planned = owner._check_specs(pack, owner.OWNER_SPECS, tmp_path / "pub", tmp_path / "ex")
    assert planned == PLANS[pathway]


def drive_cp6(root: Path) -> OwnerWorkflow:
    """The R6 run to CP-6 settled: CP-0, CP-1, CP-1A, CP-2, CP-3, CP-5 (the oracle premise), then
    the oracle's `committee_challenge` literal. CP-MODEL is not requested in R6."""
    runs.RUN = "R6"
    workflow, pack = runs.promoted(CASE, root)
    runs.through_cp2(workflow, pack, CASE)
    cp3 = runs.drive_cp3(workflow, CASE)
    assert cp3["status"] == "valid", cp3["issues"]
    # CP-5: the cp5-owner literal, each {{FIG:name}} replaced by the bound CP-1 fact_id
    cp5 = json.loads((runs.ROOT / "cases/cp5-owner/submissions.json").read_text())[CASE]
    text = json.dumps(cp5)
    names = runs.figure_names(text)
    ids = runs.cp1_bindings(workflow._store, names)
    for name in names:
        text = text.replace("{{FIG:" + name + "}}", ids[name][0])
    workflow.read_inputs()
    review = workflow.submit_review(text)
    assert review["status"] == "valid", review["issues"]
    # CP-6: the oracle literal, figures bound like CP-3
    # `runs.literal` has no committee_challenge case: read the frozen literal from the oracle
    payload = json.dumps(runs.oracle()["submissions"][CASE][STEP], ensure_ascii=False)
    payload = runs.bind_figures(
        payload, runs.cp1_bindings(workflow._store, runs.figure_names(payload))
    )
    workflow.read_inputs()
    outcome = workflow.submit_review(payload)
    assert outcome["status"] == "valid", outcome["issues"]
    return workflow


@pytest.fixture
def r6(tmp_path: Path) -> Any:
    saved = runs.RUN
    try:
        yield drive_cp6(tmp_path)
    finally:
        runs.RUN = saved


def _attempt(store: Execution) -> Any:
    snapshot = store.read()
    head = next(h for h in snapshot.heads if h.module_id == "CP-6")
    return snapshot, next(a for a in snapshot.attempts if a.result_sha256 == head.result_sha256)


@promotion
def test_cp6_view_matches_module_context(r6: OwnerWorkflow) -> None:
    store = r6._store
    _, attempt = _attempt(store)
    digest, body = cp6.view(store, attempt)
    assert body == json.dumps(
        module_context(store, attempt, STEP), ensure_ascii=False, separators=(",", ":")
    )
    assert digest == hashlib.sha256(body.encode()).hexdigest()
    cp6.probe(store, store.read(), attempt)  # the untampered head re-derives


@promotion
def test_cp6_probe_rejects_tampered_head(r6: OwnerWorkflow) -> None:
    store = r6._store
    snapshot, attempt = _attempt(store)
    step = attempt.steps[0]
    report = json.loads(store.step_output(step.output_sha256 or ""))
    report = copy.deepcopy(report)
    report["limitations"] = [*report.get("limitations", []), "forged limitation"]
    forged_step = step.model_copy(update={"output_sha256": store._store(json.dumps(report))})
    forged_attempt = attempt.model_copy(update={"steps": (forged_step,)})
    forged = snapshot.model_copy(
        update={
            "attempts": tuple(
                forged_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            )
        }
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp6.probe(store, forged, forged_attempt)
