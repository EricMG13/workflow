"""Pathway score: reads an orchestrator run directory and scores every module of the pathway preset
(spec 7.4, 10.3). Reads only; nothing is written into the run directory (C4)."""

from __future__ import annotations

import re
from collections.abc import Mapping as MappingABC
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from deploy_vii.contracts import PATHWAY_MODULES, Contract, Module, PathwayId
from deploy_vii.execution import Execution
from deploy_workflow.model_testing.cases import CaseError, GoldenCase
from deploy_workflow.model_testing.mapping import Mapping
from deploy_workflow.model_testing.records import JournalError, RunMeta, read_run
from deploy_workflow.model_testing.scoring import HeadStatus, ModuleScore, score_module
from deploy_workflow.owner_rendering import verify_owner_rendered_slice
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt
from deploy_workflow.workflow import WorkflowError

_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")


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
    render_problem: str | None = None
    passed: bool


def _receipt(path: Path) -> OwnerRunReceipt:
    try:
        return OwnerRunReceipt.model_validate_json(path.read_bytes())
    except ValidationError:
        raise JournalError("owner-run.json: not a valid owner run receipt") from None


def receipt_refusals(run_dir: Path) -> dict[str, tuple[str, ...]]:
    """The inputs each refused module named as missing, read from the run's owner receipt (the
    O3 ``RefusedBegin.missing_inputs`` record). A module whose refusal names nothing is left out;
    a directory without a receipt has none."""
    path = run_dir / "owner-run.json"
    if not path.is_file():
        return {}
    receipt = _receipt(path)
    return {r.module_id: tuple(r.missing_inputs) for r in receipt.refusals if r.missing_inputs}


def _check_refusal_names(pathway: PathwayId, named: MappedRefusals) -> None:
    """Every module and input a refusal names must belong to the pathway preset; anything else
    is refused, never scored as an excused gap."""
    preset = set(PATHWAY_MODULES[pathway])
    for module_id, inputs in named.items():
        if module_id not in preset:
            raise ValueError(f"refusals name module {module_id}, outside the {pathway} preset")
        for name in inputs:
            if name not in preset:
                raise ValueError(
                    f"refusal of {module_id} names input {name}, outside the {pathway} preset"
                )


def _problem_code(error: ValueError) -> str:
    """The refusal's short code. Both verifiers refuse with a bare code (``WorkflowError.code``
    or an ``owner_render_*`` message); any other text could carry a path or an input value, so it
    is withheld."""
    code = error.code if isinstance(error, WorkflowError) else str(error)
    return code if _CODE.fullmatch(code) else "unrecognised refusal"


def _rendered(run_dir: Path, receipt: OwnerRunReceipt) -> tuple[bool, str | None]:
    """Whether the receipt verifies against the store and the delivery re-derives byte for byte,
    and the refusal code when not. Both verifiers refuse with a ``ValueError``; that is the only
    failure read as 'not rendered'."""
    execution = run_dir / "execution"
    publication = run_dir / "publication"
    shown = publication if publication.exists() else None
    try:
        verify_owner_run_receipt(Execution(execution), receipt, publication_directory=shown)
        verify_owner_rendered_slice(
            execution, run_dir / "owner-run.json", shown, run_dir / "delivery"
        )
    except ValueError as error:
        return False, _problem_code(error)
    return True, None


def _check_identity(receipt: OwnerRunReceipt, meta: RunMeta) -> None:
    """The receipt must belong to the run directory it sits in. Names the field only."""
    if receipt.run.run_id != meta.run_id:
        raise JournalError("owner-run.json: run.run_id differs from run.json")
    if receipt.run.pathway != meta.pathway:
        raise JournalError("owner-run.json: run.pathway differs from run.json")
    preset = set(PATHWAY_MODULES[meta.pathway])
    if any(module_id not in preset for module_id in receipt.plan):
        raise JournalError("owner-run.json: plan holds a module outside the pathway preset")


def _score_modules(
    run_dir: Path,
    receipt: OwnerRunReceipt,
    pathway: PathwayId,
    case: GoldenCase,
    mapping: Mapping,
    refusals: MappedRefusals,
) -> tuple[ModuleScore, ...]:
    store = Execution(run_dir / "execution")
    heads = {h.module_id: h for h in receipt.heads}
    refused = {r.module_id for r in receipt.refusals}
    upstream: set[str] = set()
    scores: list[ModuleScore] = []
    for module_id in PATHWAY_MODULES[pathway]:
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
    missing (``receipt_refusals`` reads them from the receipt; a refused module without an entry
    scores as refused with nothing named). Names outside the pathway preset raise ``ValueError``."""
    meta, _ = read_run(run_dir)
    if meta.case_id != case.case_id:
        raise CaseError(f"run {meta.run_id} is case {meta.case_id}, not {case.case_id}")
    if meta.pathway != case.pathway:
        raise CaseError(f"run {meta.run_id} is pathway {meta.pathway}, not {case.pathway}")
    named = {} if refusals is None else refusals
    _check_refusal_names(meta.pathway, named)
    receipt_path = run_dir / "owner-run.json"
    if receipt_path.is_file():
        receipt = _receipt(receipt_path)
        _check_identity(receipt, meta)
        modules = _score_modules(run_dir, receipt, meta.pathway, case, mapping, named)
        rendered, render_problem = _rendered(run_dir, receipt)
    else:
        render_problem = None
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
        render_problem=render_problem,
        passed=meta.outcome == "settled" and rendered and all(m.passed for m in modules),
    )
