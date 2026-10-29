"""CP-3C run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed covenant_refinancing run (CP-0, CP-1, CP-1A, CP-2, CP-2D, CP-3C) over the pinned
oracle in `cases/cp3c-owner`, driven through the public `OwnerWorkflow` API only. The upstream
literals are the S1 ones (`s1a_runs`) and the CP-2D ones (`cp2d_runs`), except two this run
ships (manifest.json#upstream_literals): the CP-0 readiness review with both consumer deltas
appended (CP-2D, then CP-3C) and the CP-1 downstream review (`submissions.json
#cp1_downstream_review`, its selectors resolved against the readiness step's
`DownstreamInputs`), which replaces S1's `{"consumers": []}`. The positive run promotes CP-1 once
(11 to 26 minutes); gap_no_repricing and blocked_cp3c fork the store before CP-3C begins,
gap_minimum_cash and begin_refused_cp2d_blocked before CP-2D begins. Nothing here asserts
expected values: the oracle files are read, never derived. Not run in Stage 2 (deferred to
Stage 5); `tests/test_connect_cp3c.py` checks its pure parts.
"""

import importlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import cp2d_runs
import s1a_runs as s1a

from deploy_vii.contracts import Run
from deploy_vii.downstream_readiness import DownstreamInputs, _evidence_tags
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/cp3c-owner"
PINS = {
    CASE / "builder/build.py": "6b6b9c2fe449ab352d976ceaa38b8d33e1bf5960ee7f441a0ef27c1c497aff5d",
    CASE / "expected.json": "168e3bee6eb444f6fe4207b961a7c7f2b3aace35b68a9ac6170696511518bad3",
    CASE / "manifest.json": "551c3125319f5dde4a2022f51a5a40f59f79880764a1dd0aac3b7cd9933fc919",
    CASE / "submissions.json": "8c2b08fa3a7022097aca03798b81a23fd678ba2654ff9ef970a4c02166c34e3c",
}
CASES = ("positive", "gap_minimum_cash", "gap_no_repricing")
TOKEN = re.compile(r"\{\{FACT:([^}]+)\}\}")
# cp1_downstream_review selectors (the literal's own wording) -> the evidence tags they name.
SELECT_TAGS: Mapping[str, frozenset[str]] = {
    "every catalogue record whose _evidence_tags contain kpi:ebitda or kpi:adjusted_ebitda": (
        frozenset({"kpi:ebitda", "kpi:adjusted_ebitda"})
    ),
    "every catalogue record whose _evidence_tags contain observation:facilities": frozenset(
        {"observation:facilities"}
    ),
}
SELECT_GAPS = "every retained gap of DownstreamInputs.narrative.gaps, in one scope per consumer"
ORACLE_FILES = ("manifest", "submissions", "expected")


def oracle() -> dict[str, Any]:
    """The oracle files; a drifted pinned file fails."""
    for path, digest in PINS.items():
        if s1a._sha(path) != digest:
            raise RuntimeError(f"oracle drift: {path.name}")
    return {name: json.loads((CASE / f"{name}.json").read_text()) for name in ORACLE_FILES}


def make_pack() -> PreparedPack:
    """The S1 positive sources with the CP-3C run (pathway covenant_refinancing; CP-1, CP-1A,
    CP-2, CP-2D, CP-3C requested): the pack hash changes with the run."""
    base = s1a.make_pack("positive")
    run = Run.model_validate_json(json.dumps(oracle()["manifest"]["run"]))
    return PreparedPack(run=run, sources=base.sources)


def cp0_text(pack: PreparedPack) -> str:
    """The S1 CP-0 readiness literal with the CP-2D and CP-3C consumer deltas appended."""
    document = json.loads(s1a.literal("positive", "readiness_review", pack))
    document["consumers"] = [
        *document["consumers"],
        *oracle()["submissions"]["cp0_consumer_deltas"],
    ]
    return json.dumps(document, ensure_ascii=False)


def start(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack()
    return OwnerWorkflow.create(root / "store", pack), pack


def downstream_review(inputs: DownstreamInputs, inputs_sha256: str) -> str:
    """`submissions.json#cp1_downstream_review` bound to the readiness step's inputs: the hash
    prefilled, each selector replaced by the ids it names (catalogue records by their evidence
    tags, every retained narrative gap), the literal's `note` and `requested_consumers` (not
    fields of `DownstreamReview`) dropped. An unknown selector fails closed."""
    literal = dict(oracle()["submissions"]["cp1_downstream_review"])
    for key in ("note", "requested_consumers"):
        literal.pop(key)
    literal["inputs_sha256"] = inputs_sha256
    catalogue = inputs.narrative.inputs.catalogue
    gaps = [gap.gap_id for gap in inputs.narrative.gaps]

    def bind(value: Any) -> Any:
        if isinstance(value, dict) and set(value) == {"select"}:
            if value["select"] == SELECT_GAPS:
                return gaps
            tags = SELECT_TAGS.get(value["select"])
            if tags is None:
                raise RuntimeError(f"unknown selector: {value['select']}")
            return [r.evidence_id for r in catalogue if _evidence_tags(r) & tags]
        if isinstance(value, dict):
            return {k: bind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bind(v) for v in value]
        return value

    return json.dumps(bind(literal), ensure_ascii=False)


def drive_cp1(workflow: OwnerWorkflow, pack: PreparedPack) -> None:
    """CP-1 to its promotion: the S1 positive stages (`s1a_runs.drive_cp1`), except the
    readiness stage, which submits this run's downstream review."""
    cp1d = importlib.import_module("cp1d_runs")
    s1a.drive_cp1(
        workflow,
        pack,
        "positive",
        context=s1a.literal("positive", "cp1_source_context", pack),
        narrative_tool_check=False,
        readiness=lambda w, ready: downstream_review(
            cp1d.downstream_inputs(w), str(ready["inputs_sha256"])
        ),
    )


def reach_cp2d(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0, CP-1, CP-1A and CP-2 settled; CP-2D begun and untouched (the slow part)."""
    workflow, pack = start(root)
    s1a.drive_cp0(workflow, pack, "positive", text=cp0_text(pack))
    drive_cp1(workflow, pack)
    for outcome in (
        s1a.drive_cp1a(workflow, pack, "positive"),
        s1a.drive_cp2(workflow, "positive", s1a.read_cp2(workflow)),
    ):
        if outcome["status"] != "valid":
            raise RuntimeError(f"upstream not valid: {outcome['issues']}")
    return workflow, pack


def reach(root: Path, template_cp2d: OwnerWorkflow, cp2d_case: str = "positive") -> OwnerWorkflow:
    """A fork of `template_cp2d` with CP-2D settled on its frozen `cp2d_case` literal; CP-3C
    begun and untouched."""
    workflow = s1a.clone_workflow(template_cp2d, root)
    outcome = cp2d_runs.drive_cp2d(workflow, cp2d_case)
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2D not valid: {outcome['issues']}")
    return workflow


def bind_facts(text: str, body: Mapping[str, Any]) -> str:
    """`{{FACT:name}}` -> the ref the read view offers for that name (the view's `facts`). An
    unknown name fails closed."""
    refs = {item["name"]: item["ref"] for item in body["facts"]}

    def replace(match: re.Match[str]) -> str:
        if match[1] not in refs:
            raise RuntimeError(f"FACT {match[1]}: not offered by the read view")
        return str(refs[match[1]])

    return TOKEN.sub(replace, text)


def drive_cp3c(workflow: OwnerWorkflow, payload: Any) -> dict[str, Any]:
    """The one read_inputs of the attempt, then `payload` with its tokens bound against the read
    body; no pack tool is offered, so no invoke is made."""
    body = json.loads(workflow.read_inputs()["body"])
    outcome: dict[str, Any] = workflow.submit_review(
        bind_facts(json.dumps(payload, ensure_ascii=False), body)
    )
    return outcome


def cp3c_closed(case: str, root: Path, template: OwnerWorkflow) -> tuple[Path, Path]:
    """One closed CP-3C run of `case` under `root`: (store, sealed receipt). `template` is a
    workflow from `reach_cp2d` (CP-2D begun, untouched); it is forked, not consumed."""
    expected = oracle()["expected"]["cases"][case]
    workflow = reach(root, template, expected["consumes_cp2d_case"])
    outcome = drive_cp3c(workflow, oracle()["submissions"]["cp3c"][case])
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-3C not valid: {outcome['issues']}")
    return root / "store", seal(workflow, root)


# --- acceptance drivers (lease Refusals; expected.json#negative_cases) -------------------------


def blocked_cp3c(root: Path, template: OwnerWorkflow) -> tuple[OwnerWorkflow, list[dict[str, Any]]]:
    """`blocked_cp3c`: attempts 0 and 1 are both invalid, so CP-3C settles blocked; the walk
    completes and a receipt can be written."""
    workflow = reach(root, template)
    outcomes = [
        drive_cp3c(workflow, oracle()["submissions"]["cp3c_blocked"][attempt])
        for attempt in ("attempt_0", "attempt_1")
    ]
    return workflow, outcomes


def begin_refused_cp2d_blocked(
    root: Path, template: OwnerWorkflow
) -> tuple[OwnerWorkflow, dict[str, Any]]:
    """`begin_refused_cp2d_blocked`: CP-2D attempts 0 and 1 submit the frozen cp2d_blocked
    literals, so CP-2D settles blocked and the walk retains the CP-3C begin as a refusal (no
    CP-3C attempt). Returns the CP-2D attempt-1 outcome, which carries the refusal."""
    workflow = s1a.clone_workflow(template, root)
    blocked = cp2d_runs.oracle()["submissions"]["cp2d_blocked"]
    outcome: dict[str, Any] = {}
    for attempt in ("attempt_0", "attempt_1"):
        workflow.read_inputs()
        text = cp2d_runs.bind_facts(json.dumps(blocked[attempt], ensure_ascii=False), workflow)
        outcome = workflow.submit_review(text)
        if outcome["status"] != "invalid":
            raise RuntimeError(f"CP-2D {attempt} not invalid: {outcome['status']}")
    return workflow, outcome


def seal(workflow: OwnerWorkflow, root: Path) -> Path:
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "owner-receipt.json"


def verify_receipt(store_root: Path, receipt: Any) -> None:
    """`verify_owner_run_receipt` over a sealed run; a tamper raises `WorkflowError`."""
    from deploy_workflow.owner_workflow import verify_owner_run_receipt

    verify_owner_run_receipt(Execution(store_root), receipt)
