"""Pathway score: reads an orchestrator run directory and scores every module of the plan
(spec 7.4, 10.3). Reads only; nothing is written into the run directory (C4)."""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from deploy_vii.contracts import PATHWAY_MODULES, Contract, Module
from deploy_vii.execution import Execution
from deploy_workflow.model_testing.cases import CaseError, GoldenCase
from deploy_workflow.model_testing.mapping import Mapping
from deploy_workflow.model_testing.records import JournalError, read_run
from deploy_workflow.model_testing.scoring import HeadStatus, ModuleScore, score_module
from deploy_workflow.owner_rendering import verify_owner_rendered_slice
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt


class PathwayScore(Contract):
    run_id: str
    case_id: str
    pathway: str
    config_id: str
    mode: Literal["offline", "live"]
    outcome: Literal["settled", "stopped"]
    stopped_reason: str | None
    ruling_sha256: str | None
    modules: tuple[ModuleScore, ...]
    rendered: bool
    passed: bool


def _receipt(path: Path) -> OwnerRunReceipt:
    try:
        return OwnerRunReceipt.model_validate_json(path.read_bytes())
    except ValidationError:
        raise JournalError("owner-run.json: not a valid owner run receipt") from None


def _rendered(run_dir: Path, receipt: OwnerRunReceipt) -> bool:
    """Whether the receipt verifies against the store and the delivery re-derives byte for byte.
    Both verifiers refuse with a ``ValueError``; that is the only failure read as 'not rendered'."""
    execution = run_dir / "execution"
    publication = run_dir / "publication"
    shown = publication if publication.exists() else None
    try:
        verify_owner_run_receipt(Execution(execution), receipt, publication_directory=shown)
        verify_owner_rendered_slice(
            execution, run_dir / "owner-run.json", shown, run_dir / "delivery"
        )
    except ValueError:
        return False
    return True


def _score_modules(
    run_dir: Path,
    receipt: OwnerRunReceipt,
    case: GoldenCase,
    mapping: Mapping,
    refusals: MappedRefusals,
) -> tuple[ModuleScore, ...]:
    store = Execution(run_dir / "execution")
    heads = {h.module_id: h for h in receipt.heads}
    refused = {r.module_id for r in receipt.refusals}
    upstream: set[str] = set()
    scores: list[ModuleScore] = []
    for module_id in receipt.plan:
        module: Module | None = None
        status: HeadStatus
        head = heads.get(module_id)
        if head is not None:
            module, status = store.result(head.result_sha256), head.status
        elif module_id in refused:
            status = "refused"
        else:
            status = "absent"
        score = score_module(
            module,
            module_id,
            status,
            case,
            mapping,
            frozenset(upstream),
            refusals.get(module_id, ()),
        )
        upstream.update(f.fact_id for f in score.facts if f.outcome == "mismatch")
        scores.append(score)
    return tuple(scores)


MappedRefusals = MappingABC[str, tuple[str, ...]]


def score_run(
    run_dir: Path,
    case: GoldenCase,
    mapping: Mapping,
    *,
    refusals: MappedRefusals | None = None,
) -> PathwayScore:
    """Score one run directory. ``refusals`` maps a refused module to the inputs it named as
    missing (empty until the orchestrator records them; a refused module without an entry scores
    as refused with nothing named)."""
    meta, _ = read_run(run_dir)
    if meta.case_id != case.case_id:
        raise CaseError(f"run {meta.run_id} is case {meta.case_id}, not {case.case_id}")
    if meta.pathway != case.pathway:
        raise CaseError(f"run {meta.run_id} is pathway {meta.pathway}, not {case.pathway}")
    named = {} if refusals is None else refusals
    receipt_path = run_dir / "owner-run.json"
    if receipt_path.is_file():
        receipt = _receipt(receipt_path)
        modules = _score_modules(run_dir, receipt, case, mapping, named)
        rendered = _rendered(run_dir, receipt)
    else:
        modules = tuple(
            score_module(None, module_id, "absent", case, mapping, frozenset())
            for module_id in PATHWAY_MODULES[meta.pathway]
        )
        rendered = False
    return PathwayScore(
        run_id=meta.run_id,
        case_id=meta.case_id,
        pathway=meta.pathway,
        config_id=meta.config_id,
        mode=meta.mode,
        outcome=meta.outcome,
        stopped_reason=meta.stopped_reason,
        ruling_sha256=meta.ruling_sha256,
        modules=modules,
        rendered=rendered,
        passed=meta.outcome == "settled" and rendered and all(m.passed for m in modules),
    )
