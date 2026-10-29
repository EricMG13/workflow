"""CP-2D run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed covenant_refinancing run (CP-0, CP-1, CP-1A, CP-2, CP-2D) over the pinned oracle in
`cases/cp2d-owner`, driven through the public `OwnerWorkflow` API only. G2 imports `cp2d_closed`.
The positive run promotes CP-1 once (11 to 26 minutes); the long-horizon and minimum-cash-gap
cases fork the settled store before CP-2D begins, so they add attempts, not promotions. Nothing
here asserts expected values: the oracle files are read, never derived. Not run in Stage 2
(deferred to Stage 5).
"""

import json
import re
from pathlib import Path
from typing import Any

import s1a_runs as s1a

from deploy_vii.contracts import Run
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.owners import cp2d

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/cp2d-owner"
PINS = {
    CASE / "builder/build.py": "cc200e99d141b05a9d396a015d2e7d4a553cc89f7b003f92971b81a1c0568f7d",
    CASE / "expected.json": "ed36f120e432ee90de3f9d91933cb3182893e7aed370c9d38420ecfde8acc3e7",
}
CASES = ("positive", "long_horizon", "gap_minimum_cash")
TOKEN = re.compile(r"\{\{FACT:([^}]+)\}\}")


def oracle() -> dict[str, Any]:
    """The oracle files; a drifted pinned file fails. The manifest and submissions are read
    through their own pins in `cases/PINS.json` (checked by the Stage 5 run, not here)."""
    for path, digest in PINS.items():
        if s1a._sha(path) != digest:
            raise RuntimeError(f"oracle drift: {path.name}")
    return {
        "manifest": json.loads((CASE / "manifest.json").read_text()),
        "submissions": json.loads((CASE / "submissions.json").read_text()),
        "expected": json.loads((CASE / "expected.json").read_text()),
    }


def make_pack() -> PreparedPack:
    """The S1 positive sources with the CP-2D run (pathway covenant_refinancing; CP-1, CP-1A,
    CP-2, CP-2D requested): the pack hash changes with the run."""
    base = s1a.make_pack("positive")
    run = Run.model_validate_json(json.dumps(oracle()["manifest"]["run"]))
    return PreparedPack(run=run, sources=base.sources)


def cp0_text(pack: PreparedPack) -> str:
    """The S1 CP-0 readiness literal with the CP-2D consumer delta appended."""
    document = json.loads(s1a.literal("positive", "readiness_review", pack))
    document["consumers"] = [
        *document["consumers"],
        oracle()["submissions"]["cp0_consumer_delta"],
    ]
    return json.dumps(document, ensure_ascii=False)


def start(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack()
    return OwnerWorkflow.create(root / "store", pack), pack


def reach_cp2(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0, CP-1 and CP-1A settled; CP-2 begun and untouched. The slow part (CP-1 promotion)."""
    workflow, pack = start(root)
    s1a.drive_cp0(workflow, pack, "positive", text=cp0_text(pack))
    s1a.drive_cp1(workflow, pack, "positive")
    cp1a = s1a.drive_cp1a(workflow, pack, "positive")
    if cp1a["status"] != "valid":
        raise RuntimeError(f"CP-1A not valid: {cp1a['issues']}")
    return workflow, pack


def reach(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0, CP-1, CP-1A and CP-2 settled; CP-2D begun and untouched."""
    workflow, pack = reach_cp2(root)
    outcome = s1a.drive_cp2(workflow, "positive", s1a.read_cp2(workflow))
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2 not valid: {outcome['issues']}")
    return workflow, pack


def bind_facts(text: str, workflow: OwnerWorkflow) -> str:
    """`{{FACT:name}}` -> the fact id the bindings select from the settled CP-1 head. An unknown
    name fails closed."""
    store = workflow._store
    head = next(h for h in store.read().heads if h.module_id == "CP-1")
    selection = cp2d.select_cp1(store.head_module(head))
    ids = {o.name: o.fact.fact_id for o in selection.offered}

    def replace(match: re.Match[str]) -> str:
        if match[1] not in ids:
            raise RuntimeError(f"FACT {match[1]}: not selected from the CP-1 head")
        return ids[match[1]]

    return TOKEN.sub(replace, text)


def literal(case: str, workflow: OwnerWorkflow) -> str:
    entry = oracle()["submissions"]["cp2d"][case]
    return bind_facts(json.dumps(entry, ensure_ascii=False), workflow)


def drive_cp2d(workflow: OwnerWorkflow, case: str, *, text: str | None = None) -> dict[str, Any]:
    """The one read_inputs of the step, then the literal (or `text`); no pack tool is offered, so
    every invoke would be a refused receipt and none is made."""
    workflow.read_inputs()
    payload = literal(case, workflow) if text is None else text
    return workflow.submit_review(payload)


def cp2d_closed(case: str, root: Path, template: OwnerWorkflow | None = None) -> tuple[Path, Path]:
    """One closed CP-2D run of `case` under `root`: (store, sealed receipt). `template` is a
    workflow from `reach` (CP-2D begun, untouched); it is forked, not consumed."""
    if template is None:
        workflow, _ = reach(root)
    else:
        workflow = s1a.clone_workflow(template, root)
    outcome = drive_cp2d(workflow, case)
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2D not valid: {outcome['issues']}")
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json"


# --- acceptance drivers (docs/CP2D-OWNER-LEASE.md Refusals; expected.json#negative_cases) --------


def blocked_cp2d(root: Path, template: OwnerWorkflow) -> OwnerWorkflow:
    """`blocked_cp2d`: attempts 0 and 1 are both invalid, so CP-2D settles blocked; the walk
    completes and a receipt can be written."""
    workflow = s1a.clone_workflow(template, root)
    blocked = oracle()["submissions"]["cp2d_blocked"]
    for attempt in ("attempt_0", "attempt_1"):
        workflow.read_inputs()
        outcome = workflow.submit_review(
            bind_facts(json.dumps(blocked[attempt], ensure_ascii=False), workflow)
        )
        if outcome["status"] != "invalid":
            raise RuntimeError(f"{attempt} not invalid: {outcome['status']}")
    return workflow


def begin_refused_cp2_blocked(root: Path, template_cp2: OwnerWorkflow) -> OwnerWorkflow:
    """`begin_refused_cp2_blocked`: CP-2 is settled blocked (its attempts 0 and 1 both fail a rule,
    the unreplaced {{FIG}} literal), so CP-2D's begin is refused (edge_rule block) and the walk
    ends with a retained refusal and no CP-2D attempt."""
    workflow = s1a.clone_workflow(template_cp2, root)
    raw = s1a.literal("positive", "credit_synthesis")
    for _ in range(2):
        s1a.read_cp2(workflow)
        outcome = workflow.submit_review(raw)
        if outcome["status"] != "invalid":
            raise RuntimeError(f"CP-2 literal not invalid: {outcome['status']}")
    return workflow


def seal(workflow: OwnerWorkflow, root: Path) -> Path:
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "owner-receipt.json"


def verify_receipt(store_root: Path, receipt: Any) -> None:
    """`verify_owner_run_receipt` over a sealed run; a tamper raises `WorkflowError`
    (`identity_mismatch`), a stale submit `stale_binding`, a premature submit `not_permitted`."""
    from deploy_workflow.owner_workflow import verify_owner_run_receipt

    verify_owner_run_receipt(Execution(store_root), receipt)
