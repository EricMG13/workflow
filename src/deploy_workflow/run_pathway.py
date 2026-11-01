"""``run_pathway``: the entry point that joins O2's input checks to O5's model tool loop (O2 Task 3).

The order is fixed: ``check_arguments`` (writes nothing), ``stage_sources``, then ``_run_pathway``,
which creates the ``OwnerWorkflow``, drives it step by step through ``ToolLoop``, calls
``workflow.publish()`` at the publisher's stop, and hands the finished walk to ``_finish_run``
(receipt, verify, render, verify the render, ``run.json`` last).

A named fault ends the run as ``stopped``: ``StepStopped``, any ``BudgetError``, ``RecordingMissing``,
``WorkflowError``, ``NoPrompt``, ``PromptError``, and a ``ValueError`` from prepare or from the
render and its verify. ``run.json`` records the outcome and a redacted reason. Any other exception
propagates and leaves the run directory WITHOUT ``run.json``: a crashed run is detectable by that
absence. Nothing here reads the environment or the network; the live adapter reads keys only inside
its own ``complete``, and this module's text is redacted by the key pattern alone.
"""

import contextlib
import json
import os
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from deploy_vii.contracts import PathwayId
from deploy_vii.execution import Execution
from deploy_vii.live.prompts import STEP_CONTRACTS, PromptError
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_vii.registry import plan
from deploy_workflow.model.adapter import LiveAdapter, ModelAdapter, RecordingMissing
from deploy_workflow.model.budget import Budget, BudgetError
from deploy_workflow.model.loop import (
    PromptFor,
    StepStopped,
    ToolLoop,
    contract_prompt_for,
    contract_tools_for,
)
from deploy_workflow.model.pricing import money_text
from deploy_workflow.model.record import CallLog
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import Message, ModelSpec
from deploy_workflow.owner_rendering import render_owner_slice, verify_owner_rendered_slice
from deploy_workflow.owner_workflow import (
    OWNER_SPECS,
    OwnerBinding,
    OwnerWorkflow,
    StepSpec,
    verify_owner_run_receipt,
)
from deploy_workflow.run_inputs import (
    _SUFFIX,
    HTML_MEDIA,
    CaseSource,
    CheckedRun,
    RunInputError,
    RunOutcome,
    check_arguments,
    stage_sources,
)
from deploy_workflow.workflow import WorkflowError

# The longest reply the loop will reserve for. The reservation is sized from this, so a larger
# value needs a larger cap; 128k is the most O5 accepts (spec section 8).
MAX_OUTPUT_TOKENS = 32_768

PromptFactory = Callable[[PreparedPack], PromptFor]
_MEDIA_OF_SUFFIX = {suffix: media for media, suffix in _SUFFIX.items()}


class NoPrompt(Exception):
    """No prompt composer exists for this step yet (O6 supplies the rest); the run stops."""

    def __init__(self, step: str) -> None:
        super().__init__(step)
        self.step = step


def _default_prompt_for(pack: PreparedPack) -> PromptFor:
    """O5's contract composer for a step that has a ``STEP_CONTRACTS`` entry; a named refusal for
    every other step. It is the real composer where one exists, never a placeholder prompt."""
    composer = contract_prompt_for(pack)

    def prompt_for(
        binding: OwnerBinding, spec: StepSpec, issues: tuple[str, ...]
    ) -> tuple[Message, ...]:
        if binding.step_id not in STEP_CONTRACTS:
            raise NoPrompt(binding.step_id)
        return composer(binding, spec, issues)

    return prompt_for


_FAULTS = (StepStopped, BudgetError, RecordingMissing, WorkflowError, NoPrompt, PromptError)


@dataclass(frozen=True)
class _Meta:
    """What ``run.json`` records besides the outcome."""

    checked: CheckedRun
    entries: tuple[dict[str, Any], ...]
    live: bool
    redactor: Redactor


def _source_entries(
    checked: CheckedRun, sources: Sequence[CaseSource], context: Path
) -> tuple[dict[str, Any], ...]:
    """``run.json`` ``sources``: the caller's path and media type, the hash of the original bytes,
    and, for a converted HTML source, the hash of the staged (converted) bytes."""
    staged = {item.source_id: item for item in checked.files}
    entries: list[dict[str, Any]] = [
        {
            "source_id": item.source_id,
            "path": str(item.path),
            "sha256": staged[item.source_id].original_sha256,
            "media_type": item.media_type,
            "converted_sha256": staged[item.source_id].sha256
            if item.media_type == HTML_MEDIA
            else None,
        }
        for item in sources
    ]
    entries.append(
        {
            "source_id": staged["context"].source_id,
            "path": str(context),
            "sha256": staged["context"].sha256,  # the context is staged unconverted
            "media_type": "text/plain",
            "converted_sha256": None,
        }
    )
    return tuple(entries)


def _staged_entries(checked: CheckedRun, run_dir: Path) -> tuple[dict[str, Any], ...]:
    """The entries when the caller's paths are not known (the authoring harness): the staged
    files. A file whose staged hash differs from its original was converted from HTML."""
    entries: list[dict[str, Any]] = []
    for item in checked.files:
        converted = item.sha256 != item.original_sha256
        if item.source_id == "context":
            media = "text/plain"
        elif converted:
            media = HTML_MEDIA
        else:
            media = _MEDIA_OF_SUFFIX[Path(item.filename).suffix]
        entries.append(
            {
                "source_id": item.source_id,
                "path": str(run_dir / "sources" / item.filename),
                "sha256": item.original_sha256,
                "media_type": media,
                "converted_sha256": item.sha256 if converted else None,
            }
        )
    return tuple(entries)


def _fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_run_json(run_dir: Path, meta: _Meta, outcome: str, stopped_reason: str | None) -> None:
    """Write ``run.json`` last: a temp file in ``run_dir``, fsync, ``os.replace``."""
    checked = meta.checked
    body: dict[str, Any] = {
        "case_id": checked.case_id,
        "pathway": checked.pathway,
        "config_id": checked.model.config_id,
        "run_id": checked.run_id,
        "mode": "live" if meta.live else "offline",
        "cap_usd": money_text(checked.cap_usd),
        "sources": list(meta.entries),
        "cp_dr_invoked": False,
        "replayed_from_run": None,
        "outcome": outcome,
        "stopped_reason": stopped_reason,
    }
    if meta.live and checked.gate is not None:
        body["ruling_path"] = str(checked.gate.path)
        body["ruling_sha256"] = checked.gate.sha256
        body["ruling_date"] = checked.gate.date.isoformat()
    data = (json.dumps(meta.redactor.json_value(body), indent=2) + "\n").encode()
    temp = run_dir / "run.json.tmp"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, run_dir / "run.json")
    _fsync_directory(run_dir)


def _stop(run_dir: Path, meta: _Meta, reason: str, spent: Decimal) -> RunOutcome:
    """End the run as ``stopped``: the redacted reason goes to ``run.json``. Callers build
    ``reason`` inside their ``except`` and call this after leaving it, so a failure to write
    ``run.json`` is not chained to the raw fault."""
    clean = meta.redactor.text(reason)
    _write_run_json(run_dir, meta, "stopped", clean)
    return RunOutcome(meta.checked.run_id, run_dir, "stopped", clean, spent)


@dataclass(frozen=True)
class _Fault:
    """A named fault, as redacted-on-write text and the spend so far; the run then stops."""

    reason: str
    spent: Decimal


def _fault_reason(fault: Exception, redactor: Redactor) -> str:
    if isinstance(fault, StepStopped):
        return redactor.text(str(fault))
    return f"{type(fault).__name__}: {redactor.text(str(fault))}"


def _render(workflow: OwnerWorkflow, run_dir: Path, shown: Path | None) -> str | None:
    """Render and verify the delivery; the fault text of a ``ValueError``, else ``None``."""
    execution, receipt_path, delivery = (
        run_dir / "execution",
        run_dir / "owner-run.json",
        run_dir / "delivery",
    )
    try:
        render_owner_slice(execution, receipt_path, shown, delivery)
        verify_owner_rendered_slice(execution, receipt_path, shown, delivery)
    except ValueError as error:
        return f"render: {error}"
    return None


def _finish_run(workflow: OwnerWorkflow, run_dir: Path, meta: _Meta, budget: Budget) -> RunOutcome:
    """After the walk: receipt, verify it, render, verify the render, then ``run.json`` last.
    A ``ValueError`` from the render or its verify is the fault ``render: <code>``; the receipt
    and any delivery already written are kept as evidence."""
    receipt_path = run_dir / "owner-run.json"
    publication = run_dir / "publication"
    shown = publication if publication.exists() else None
    receipt = workflow.write_receipt(receipt_path)
    verify_owner_run_receipt(Execution(run_dir / "execution"), receipt, publication_directory=shown)
    failure = _render(workflow, run_dir, shown)
    if failure is not None:
        return _stop(run_dir, meta, failure, budget.spent)
    _write_run_json(run_dir, meta, "settled", None)
    return RunOutcome(meta.checked.run_id, run_dir, "settled", None, budget.spent)


def _drive(workflow: OwnerWorkflow, loop: ToolLoop, pack: PreparedPack) -> str | None:
    """Run every step. The loop returns at the publisher's stop (or when the walk ends refused);
    ``publish`` runs there once and the walk resumes after it. A refused publication that ends the
    walk is not a fault (O1 Q1); one that leaves the walk open is, and its code is returned as the
    stop reason (``publish: <code>``) so that no receipt is attempted."""
    loop.run()
    has_publisher = any(
        OWNER_SPECS[m].kind == "deterministic" for m in plan(pack.run.requested_modules)
    )
    if not has_publisher:
        return None
    published = workflow.publish()
    if published["next_step"] is not None:
        loop.run()
    # The walk's phase has no public reader yet (O5 Q6); "complete" means the walk ended.
    elif published["status"] != "ok" and workflow._phase != "complete":
        return f"publish: {published['error_code']}"
    return None


def _stages(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    prompt_for: PromptFactory,
    meta: _Meta,
) -> RunOutcome | _Fault:
    redactor, execution = meta.redactor, run_dir / "execution"
    try:
        pack = load_pack(run_dir / "pack")
    except ValueError as error:
        return _Fault(f"prepare: {error}", Decimal(0))
    try:
        workflow = OwnerWorkflow.create(
            execution, pack, publication_directory=run_dir / "publication"
        )
    except WorkflowError as error:
        return _Fault(f"workflow: {error.code}", Decimal(0))
    budget = Budget(checked.cap_usd, execution)
    loop = ToolLoop(
        workflow,
        adapter,
        budget,
        CallLog(run_dir, redactor),
        prompt_for(pack),
        contract_tools_for,
        redactor,
        time.time,
        time.sleep,
        execution=Execution(execution),
        spec=checked.model,
        case_id=checked.case_id,
        pathway=checked.pathway,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    try:
        refused = _drive(workflow, loop, pack)
        if refused is not None:
            return _Fault(refused, budget.spent)
        return _finish_run(workflow, run_dir, meta, budget)
    except _FAULTS as fault:
        return _Fault(_fault_reason(fault, redactor), budget.spent)


def _walk(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    prompt_for: PromptFactory,
    meta: _Meta,
) -> RunOutcome:
    result = _stages(checked, run_dir, adapter, prompt_for, meta)
    if isinstance(result, _Fault):
        return _stop(run_dir, meta, result.reason, result.spent)
    return result


@contextlib.contextmanager
def _redacted_stderr(redactor: Redactor) -> Iterator[None]:
    """Route stderr through the redactor; closing the stream writes (redacted) any partial line."""
    stream = redactor.redact_stream(sys.stderr)
    try:
        with contextlib.redirect_stderr(stream):
            yield
    finally:
        stream.close()


def _run_pathway(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    prompt_for: PromptFactory = _default_prompt_for,
    *,
    entries: tuple[dict[str, Any], ...] | None = None,
) -> RunOutcome:
    """Run the walk over a staged ``run_dir``. No adapter-type check here (``check_arguments``
    owns it), so the authoring harness can drive it with a test adapter. While it runs, stderr
    passes through the redactor."""
    redactor = Redactor()
    meta = _Meta(
        checked,
        _staged_entries(checked, run_dir) if entries is None else entries,
        type(adapter) is LiveAdapter,
        redactor,
    )
    with _redacted_stderr(redactor):
        return _walk(checked, run_dir, adapter, prompt_for, meta)


def _stage(
    checked: CheckedRun,
    run_dir: Path,
    entries: tuple[dict[str, Any], ...],
    live: bool,
    redactor: Redactor,
) -> RunOutcome | None:
    """Stage the sources; a ``ValueError`` from prepare stops the run (``prepare: <text>``)."""
    try:
        stage_sources(checked, run_dir)
    except RunInputError:
        raise
    except ValueError as error:
        failure = f"prepare: {error}"
    else:
        return None
    return _stop(run_dir, _Meta(checked, entries, live, redactor), failure, Decimal(0))


def run_pathway(
    *,
    case_id: str,
    sources: Sequence[CaseSource],
    context: Path,
    pathway: PathwayId,
    model: ModelSpec,
    adapter: ModelAdapter,
    cap_usd: Decimal,
    run_dir: Path,
    run_id: str,
    cp_dr: bool = False,
) -> RunOutcome:
    """Check, stage, run, with stderr redacted throughout. A refused argument raises and writes
    nothing; a named fault after the first write returns a ``stopped`` outcome with ``run.json``.
    Any other exception propagates and leaves ``run_dir`` without ``run.json``, with one
    exception of O5's: a failure inside a model tool call is caught by the loop and stops the run
    as a named ``StepStopped``."""
    redactor = Redactor()
    with _redacted_stderr(redactor):
        checked = check_arguments(
            case_id=case_id,
            sources=sources,
            context=context,
            pathway=pathway,
            model=model,
            adapter=adapter,
            cap_usd=cap_usd,
            run_dir=run_dir,
            run_id=run_id,
            cp_dr=cp_dr,
        )
        entries = _source_entries(checked, sources, context)
        staged = _stage(checked, run_dir, entries, type(adapter) is LiveAdapter, redactor)
        if staged is not None:
            return staged
        return _run_pathway(checked, run_dir, adapter, entries=entries)


__all__ = ["NoPrompt", "run_pathway"]
