"""CP-DR (deep research, LOCAL lineage): the owner core of the steps ``brief`` and ``research``.

The ``brief`` step tailors the locked question list: the model writes the six default questions
and its own after them, Python puts the run's context questions first, bounds the list to 32 from
the tail, hashes it and locks it as ``research/brief.json`` (``research/brief.py``). The
``research`` step answers the locked brief from the held sources, ``ev-*`` items included; Python
checks the answers (``research/review.py``, ``research/steps.py``), composes TDR.1-3
(``research/tables.py``) and settles the head. Nothing here asks the model for a figure.

Protocol (docs/G1X-OWNER-CORE-PROTOCOL.md section 2): ``STEP_IDS``, ``SCHEMAS``, ``QUALIFICATION``,
``RULES``, ``ENTRY_VALIDATOR``, ``brief_view``, ``research_view``, ``probe`` and ``submit``. The
validators read the store only (the brief is the ``brief`` step's retained output), so the verifier
replays them at a historical snapshot; the files outside the store are the lock
(``research/brief.json``), the evidence record (``research/evidence.json``) and the staged item
texts, read in ``submit`` and the views and named when they are missing. ``check_begin`` runs
before the CP-DR attempt is begun (anchors, O7-R20); ``untrusted_items`` and ``dossier_input`` are
the run's hooks.
"""

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from deploy_vii.contracts import Contract, Module, Run, Source
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepSubmission,
    StepValidation,
    bounded_issues,
    settle,
)
from deploy_vii.live.prompts import PromptError
from deploy_vii.live.schema import json_object, normalise
from deploy_vii.live.submission import Submitted, _with_rules
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import shape_issues
from deploy_workflow.context import CONTEXT_SOURCE_ID, ContextRefused, context_facts
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.prompts.fence import FenceError, UntrustedItem, data_block
from deploy_workflow.research import evidence as record
from deploy_workflow.research.anchors import SettledAnchor, check_anchors
from deploy_workflow.research.brief import (
    load_locked_brief,
    merge_questions,
    rebuild_brief,
    write_locked_brief,
)
from deploy_workflow.research.contracts import (
    RESERVED_PREFIX,
    Anchor,
    BriefInvalid,
    EvidenceItem,
    ResearchBrief,
    ResearchError,
)
from deploy_workflow.research.dossier import (
    DOSSIER_BLOCK_ID,
    DossierInput,
    breaks_a_table_cell,
    brief_json,
    render_dossier,
)
from deploy_workflow.research.intake import RefusedItem, effective_cutoff
from deploy_workflow.research.review import (
    ResearchSubmission,
    answer_counts,
    claim_states,
    research_issues,
)
from deploy_workflow.research.steps import (
    RESEARCH_BRIEF_INPUT,
    BriefSubmission,
    brief_issues,
    brief_view_body,
    candidate_inputs,
    research_rules,
    research_view_body,
    tailored_of,
)
from deploy_workflow.research.tables import Composed, compose
from deploy_workflow.research.tables import dossier_input as tables_dossier_input
from deploy_workflow.workflow import WorkflowError

if TYPE_CHECKING:
    from deploy_workflow.owner_workflow import OwnerBinding, StepSpec

MODULE_ID = "CP-DR"
BRIEF_STEP = "brief"
RESEARCH_STEP = "research"
STEP_IDS = (BRIEF_STEP, RESEARCH_STEP)
SCHEMAS: Mapping[str, type[Contract]] = {
    BRIEF_STEP: BriefSubmission,
    RESEARCH_STEP: ResearchSubmission,
}
QUALIFICATION = Qualification(implementation="implemented")
RULES = research_rules
BRIEF_FILE = "brief.json"
DOSSIER_FILE = "dossier.md"
ATTACHMENTS_FILE = "attachments.json"
NOT_LOCKED = "brief is not locked: research/brief.json is missing"
RELOCKED = (
    "the brief is locked by an earlier attempt of this run; submit the same questions as that "
    "attempt"
)
DOSSIER_LOCATOR = "research/dossier.md"
CONSUMERS = ("CP-1C", "CP-2")  # the modules whose prompt carries the dossier block
ROOT_NOT_OBJECT = "(root): payload is not a JSON object the journal can store"


def research_dir(store: Execution) -> Path:
    """``<run>/research``: the execution directory is ``<run>/execution`` (or a test's ``store``)."""
    return store.directory.parent / record.RESEARCH_DIR


def _parse[T: Contract](model: type[T], text: str) -> T | tuple[str, ...]:
    """The submission, or the shape issues of text that is not one. ``json_object`` is the bounded,
    storable parse (protocol section 6); text it refuses never reaches the schema."""
    if json_object(text) is None:
        return (ROOT_NOT_OBJECT,)
    try:
        return model.model_validate_json(text)
    except ValidationError as error:
        return bounded_issues(shape_issues(error))


def _valid_step(attempt: Attempt, step_id: str) -> StepSubmission | None:
    return next((s for s in attempt.steps if s.step_id == step_id and s.status == "valid"), None)


def _brief_of(store: Execution, attempt: Attempt) -> ResearchBrief:
    """The locked brief as the ``brief`` step retained it (its canonical JSON)."""
    step = _valid_step(attempt, BRIEF_STEP)
    if step is None or step.output_sha256 is None:
        raise WorkflowError("identity_mismatch")
    return rebuild_brief(json.loads(store.step_output(step.output_sha256)))


def _evidence_rows(store: Execution) -> tuple[Mapping[str, Any], ...]:
    """The staged evidence record; a missing or damaged one is the named ``evidence_unrecorded``,
    never an empty list (the ``ev-*`` calls and the views cannot be judged without it)."""
    try:
        return record.read_evidence(research_dir(store) / record.EVIDENCE_FILE)
    except record.EvidenceRecordInvalid:
        raise WorkflowError("evidence_unrecorded") from None


def _items(rows: Sequence[Mapping[str, Any]]) -> tuple[EvidenceItem, ...]:
    return tuple(
        EvidenceItem(
            item_id=row["item_id"],
            origin=row["origin"],
            sha256=row["sha256"],
            locator=row["locator"],
            published=None if row["published"] is None else date.fromisoformat(row["published"]),
            family=row["family"],
        )
        for row in rows
    )


def _citeable(pack: PreparedPack) -> tuple[Source, ...]:
    """The held sources an answer may cite: every pack source but the run context, which is
    orientation and never cited (compose rule O3)."""
    return tuple(s for s in pack.sources if s.source_id != CONTEXT_SOURCE_ID)


def _context_questions(pack: PreparedPack) -> tuple[tuple[str, str], ...]:
    try:
        context = context_facts(pack)
    except ContextRefused:
        raise WorkflowError("identity_mismatch") from None
    if context is None:
        return ()
    return tuple((q.text, q.focus_module) for q in context.research_questions)


def _context_cutoff(pack: PreparedPack) -> date:
    """The research cutoff of the run: ``min(as_of, run.cutoff)`` of its context file (O7b-2 D9);
    the as-of date when the file is absent or sets no cutoff."""
    try:
        context = context_facts(pack)
    except ContextRefused:
        raise WorkflowError("identity_mismatch") from None
    return effective_cutoff(pack.run.as_of, "" if context is None else context.run.cutoff)


def _anchor(snapshot: ExecutionSnapshot) -> Anchor:
    """The CP-0 and CP-1 heads the brief binds (``check_begin`` ran at the begin)."""
    heads = {head.module_id: head.result_sha256 for head in snapshot.heads}
    try:
        return Anchor(cp0_sha256=heads["CP-0"], cp1_sha256=heads["CP-1"])
    except KeyError:
        raise WorkflowError("identity_mismatch") from None


def _run_issues(submitted: str, run: Run) -> tuple[str, ...]:
    """The ``run_id`` a submission names is the run's (the prepared-pack block shows it)."""
    return () if submitted == run.run_id else (f"run_id is not the run's: {run.run_id}",)


def _fence_issues(texts: Iterable[tuple[str, str]]) -> tuple[str, ...]:
    """O7-R33: a model-written text the dossier fence would refuse (a block delimiter or a
    lookalike of one) or its table cell would refuse (a line break or a ``|``) is a step issue, so the model repairs it instead of the sealed run failing at
    the dossier. The fence's own check (``data_block``), never a copy of it."""
    issues = []
    for where, text in texts:
        try:
            data_block("CONTEXT", "dossier", text)
        except FenceError:
            issues.append(f"{where}: holds a block delimiter or a lookalike of one")
        if breaks_a_table_cell(text):  # O7-R49: the dossier's cell rule, never a copy of it
            issues.append(
                f"{where}: holds a line break or a | and cannot be written in a table cell"
            )
    return tuple(issues)


def _research_texts(submission: ResearchSubmission) -> Iterator[tuple[str, str]]:
    """Every model-written text the dossier shows: claims, contrary entries, uncertainty and
    limitation."""
    for answer in submission.answers:
        qid = answer.question_id
        yield from ((qid, claim.text) for claim in answer.claims)
        for entry in answer.contrary:
            if entry.kind == "cited":
                yield qid, entry.text
            if entry.limitation is not None:
                yield qid, entry.limitation
        yield from ((qid, text) for text in (answer.uncertainty, answer.limitation) if text)


# --- the brief step ---------------------------------------------------------------------------


def _relock_issues(
    store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt, output: str
) -> tuple[str, ...]:
    """A brief locked by an earlier attempt of this run is resubmitted unchanged: the lock file
    is written once and the attempts of one run share it."""
    for earlier in snapshot.attempts:
        step = _valid_step(earlier, BRIEF_STEP)
        if (
            earlier.module_id == MODULE_ID
            and earlier.number < attempt.number
            and step is not None
            and step.output_sha256 is not None
            and store.step_output(step.output_sha256) != output
        ):
            return (RELOCKED,)
    return ()


def _validate_brief(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    parsed = _parse(BriefSubmission, store.payload(attempt.steps[-1].payload_sha256))
    if not isinstance(parsed, BriefSubmission):
        return StepValidation(issues=parsed)
    snapshot = store.read()
    run = snapshot.run
    issues = (
        *_run_issues(parsed.run_id, run),
        *brief_issues(parsed),
        *_fence_issues((q.question_id, q.text) for q in parsed.questions),
    )
    if issues:
        return StepValidation(issues=bounded_issues(issues))
    try:
        brief = ResearchBrief.build(
            issuer_id=run.issuer_id,
            run_id=run.run_id,
            as_of=run.as_of,
            cutoff=_context_cutoff(pack),
            questions=merge_questions(_context_questions(pack), tailored_of(parsed)),
            anchor=_anchor(snapshot),
            peer_pack=False,
        )
    except BriefInvalid as error:  # a model-written question the lock refuses: the model repairs
        return StepValidation(issues=bounded_issues((str(error),)))
    output = brief_json(brief)
    relocked = _relock_issues(store, snapshot, attempt, output)
    return StepValidation(issues=relocked) if relocked else StepValidation(output=output)


def _lock(store: Execution, attempt: Attempt) -> None:
    """Write ``research/brief.json`` from the valid ``brief`` step; a lock an earlier attempt wrote
    must be this brief's (``BriefInvalid("hash mismatch")`` otherwise, a fault)."""
    brief = _brief_of(store, attempt)
    path = research_dir(store) / BRIEF_FILE
    if path.exists():
        load_locked_brief(path, brief.brief_sha256)
    else:
        write_locked_brief(path, brief)


def _check_lock(store: Execution, attempt: Attempt) -> None:
    """Before a research step is journaled: the lock file exists and is the recorded brief."""
    path = research_dir(store) / BRIEF_FILE
    if not path.exists():
        raise BriefInvalid(NOT_LOCKED)
    load_locked_brief(path, _brief_of(store, attempt).brief_sha256)


# --- the research step ------------------------------------------------------------------------


def _validate_research(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    parsed = _parse(ResearchSubmission, store.payload(attempt.steps[-1].payload_sha256))
    if not isinstance(parsed, ResearchSubmission):
        return StepValidation(issues=parsed)
    found = research_issues(
        submission=parsed,
        brief=_brief_of(store, attempt),
        evidence=_items(_evidence_rows(store)),
        sources=_citeable(pack),
    )
    issues = (
        *_run_issues(parsed.run_id, store.read().run),
        *(str(issue) for issue in found),
        *_fence_issues(_research_texts(parsed)),
    )
    if issues:
        return StepValidation(issues=bounded_issues(issues))
    return StepValidation(output=parsed.model_dump_json())


def ENTRY_VALIDATOR(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The validator ``submit`` hands ``Execution.submit_step`` and the verifier replays: it
    validates the attempt's latest journaled step, ``brief`` or ``research``, and retains that
    step's canonical output. The tool-use ``RULES`` are added by the caller (``_with_rules``)."""
    if not attempt.steps:
        raise WorkflowError("identity_mismatch")
    if attempt.steps[-1].step_id == BRIEF_STEP:
        return _validate_brief(store, pack, attempt)
    return _validate_research(store, pack, attempt)


def _candidate(store: Execution, attempt: Attempt, output: str) -> Module:
    """The CP-DR candidate: TDR.1-3 over the locked brief and the reviewed submission, bound to
    the attempt's inputs, the brief and the submission."""
    submission = ResearchSubmission.model_validate_json(output)
    brief = _brief_of(store, attempt)
    composed = compose(
        brief,
        submission,
        _items(_evidence_rows(store)),
        answer_counts(submission),
        claim_states(submission, brief),
        brief.as_of.isoformat(),
    )
    run = store.read().run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=MODULE_ID,
        inputs=candidate_inputs(
            attempt.inputs,
            brief_sha256=brief.brief_sha256,
            submission_sha256=submission.content_hash(),
        ),
        facts=composed.facts,
        tables=composed.tables,
        claims=composed.claims,
        limitations=composed.limitations,
        attempt=attempt.number,
    )


# --- views ------------------------------------------------------------------------------------


def _digest(body: str) -> tuple[str, str]:
    return hashlib.sha256(body.encode()).hexdigest(), body


def brief_view(store: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of the brief step's ``read_inputs`` view: the fixed defaults, the run's
    context questions, the limits and the sources the step may read (no ``ev-*``)."""
    run = store.read().run
    pack = store.pack()
    return _digest(
        brief_view_body(
            context_questions=_context_questions(pack),
            as_of=run.as_of,
            cutoff=_context_cutoff(pack),
            sources=[
                s.source_id for s in pack.sources if not s.source_id.startswith(RESERVED_PREFIX)
            ],
        )
    )


def research_view(store: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of the research step's ``read_inputs`` view: the locked brief, the accepted
    evidence list (no text) and the sources an answer may cite."""
    return _digest(
        research_view_body(
            brief=_brief_of(store, attempt),
            evidence=_items(_evidence_rows(store)),
            source_ids=[s.source_id for s in _citeable(store.pack())],
        )
    )


# --- settlement and the verifier probe --------------------------------------------------------


def _settle(store: Execution, ticket_id: str, journal: Attempt) -> Attempt:
    outcome = ENTRY_VALIDATOR(store, store.pack(), journal)
    if outcome.issues or outcome.output is None or not outcome.retained_as(journal.steps[-1]):
        raise ValueError("Retained CP-DR output differs from trusted validation")
    candidate = _candidate(store, journal, outcome.output)
    return store.finish(
        ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("CP-DR candidate differs",),
        qualification=QUALIFICATION,
    )


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal one step (``brief`` takes no rules, ``research`` the journaled ones: every issue is
    an invalid step). A valid ``brief`` locks ``research/brief.json``; a valid ``research`` settles
    CP-DR with the Python candidate. A research step finds the lock first (a missing file is the
    named ``BriefInvalid``, an edited one the fault ``hash mismatch``)."""
    if step_id not in SCHEMAS:
        raise ValueError(f"CP-DR has the steps {', '.join(STEP_IDS)}")
    attempt = next((a for a in store.read().attempts if a.ticket_id == ticket_id), None)
    if attempt is None or attempt.module_id != MODULE_ID or attempt.status != "pending":
        raise ValueError("Ticket is absent, finished or belongs to another module")
    normalised, resolved = normalise(SCHEMAS[step_id], payload)
    if step_id == RESEARCH_STEP:
        _check_lock(store, attempt)

    def validate(pack: PreparedPack, current: Attempt) -> StepValidation:
        return ENTRY_VALIDATOR(store, pack, current)

    journal = store.submit_step(
        ticket_id,
        MODULE_ID,
        STEP_IDS,
        step_id,
        normalised,
        validate if rules is None else _with_rules(validate, rules, normalised),
    )
    last = journal.steps[-1] if journal.steps else None
    if journal.status != "finished" and last is not None and last.status == "valid":
        if last.step_id == BRIEF_STEP:
            _lock(store, journal)
        elif last.step_id == step_id:
            journal = _settle(store, ticket_id, journal)
    return Submitted(journal, normalised, resolved, (), (), None)


def _pending_through(attempt: Attempt, index: int) -> Attempt:
    """``attempt`` as the validator saw it at step ``index``: the earlier steps valid, that one
    pending (what ``Execution.submit_step`` passes its validator)."""
    step = attempt.steps[index].model_copy(
        update={"status": "pending", "output_sha256": None, "issues": ()}
    )
    return attempt.model_copy(update={"steps": (*attempt.steps[:index], step)})


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Rebuild the settled attempt over the historical snapshot: ``identity_mismatch`` unless both
    steps revalidate to their retained outputs and the candidate settles to exactly the head."""
    if tuple(s.step_id for s in attempt.steps) != STEP_IDS or any(
        s.status != "valid" for s in attempt.steps
    ):
        raise WorkflowError("identity_mismatch")
    try:
        _rebuild(store, snapshot, attempt)
    except ResearchError as error:  # O7-R54 L-a: a research-record fault is a head not authentic
        raise WorkflowError("identity_mismatch") from error


def _rebuild(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    frozen = _FrozenExecution(store, snapshot)
    pack = store.pack(snapshot)
    output = ""
    for index, step in enumerate(attempt.steps):
        outcome = ENTRY_VALIDATOR(frozen, pack, _pending_through(attempt, index))
        if (
            outcome.issues
            or outcome.output is None
            or not outcome.retained_as(step)
            or store.step_output(step.output_sha256 or "") != outcome.output
        ):
            raise WorkflowError("identity_mismatch")
        output = outcome.output
    candidate = _candidate(frozen, attempt, output)
    finished, result = settle(
        snapshot,
        attempt,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("Candidate differs",),
        pack=pack,
        load=store.head_module,
    )
    head = next(h for h in snapshot.heads if h.module_id == MODULE_ID)
    if finished != attempt or result != store.head_module(head):
        raise WorkflowError("identity_mismatch")


# --- hooks the walk and the run call ------------------------------------------------------------


def check_begin(store: Execution, snapshot: ExecutionSnapshot) -> Anchor:
    """O7-R20: before ``begin("CP-DR")``, the settled CP-0 and CP-1 heads must be a pair this run
    stands on (``research/anchors.py``); ``CpDrNotAnchored`` names the first miss and stops the run.
    The modules are read with ``store.result``, so a blocked or stale head reaches the anchor's own
    text instead of the generic missing-input error."""
    heads = {head.module_id: head for head in snapshot.heads}

    def anchored(slot: str) -> SettledAnchor | None:
        head = heads.get(slot)
        return None if head is None else SettledAnchor(head, store.result(head.result_sha256))

    return check_anchors(anchored("CP-0"), anchored("CP-1"), snapshot.run)


def _evidence_items(research: Path) -> tuple[UntrustedItem, ...]:
    """Every accepted item's full text, each checked against its recorded hash (O7-R14)."""
    items = []
    for row in record.read_evidence(research / record.EVIDENCE_FILE):
        data = (research.parent / "sources" / f"{row['item_id']}.txt").read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise record.EvidenceRecordInvalid(f"the staged text of {row['item_id']} changed")
        items.append(
            UntrustedItem(
                row["item_id"], row["sha256"], row["locator"], row["retrieved"], data.decode()
            )
        )
    return tuple(items)


def dossier_item(store: Execution, attempt: Attempt, research: Path) -> tuple[UntrustedItem, ...]:
    """O7c C3 (O7-R47 Q1): the CP-DR dossier as the one untrusted item a consumer's prompt carries.
    Built from the settled head at prompt time (``render_dossier(dossier_input(...))``, never
    ``dossier.md``); its hash is the dossier's own, the one ``run.json`` records. An attempt that
    binds no CP-DR input gets none. A ticket bound to a head that is no longer the head is refused:
    the block is never built from another head. The retrieval instant is the evidence record's
    (one intake instant for every row)."""
    bound = next((i for i in attempt.inputs if i.input_id == MODULE_ID), None)
    if bound is None:
        return ()
    head = next((h for h in store.read().heads if h.module_id == MODULE_ID), None)
    if head is None or head.result_sha256 != bound.sha256:
        raise PromptError(f"the CP-DR head is not the one {attempt.module_id} was begun on")
    text = render_dossier(dossier_input(store, head, research)).markdown
    moments = {str(r["retrieved"]) for r in record.read_evidence(research / record.EVIDENCE_FILE)}
    if len(moments) != 1:
        raise record.EvidenceRecordInvalid("the evidence record has no single retrieval instant")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return (UntrustedItem(DOSSIER_BLOCK_ID, digest, DOSSIER_LOCATOR, moments.pop(), text),)


def untrusted_items(
    research: Path, store: Execution | None = None
) -> "Callable[[OwnerBinding, StepSpec], tuple[UntrustedItem, ...]]":
    """The prompt factory's ``untrusted_for`` for a run whose staging is ``research``: the research
    step carries every accepted item's full text (O7-R14); CP-1C and CP-2 carry the dossier block
    when their ticket binds the CP-DR head (``dossier_item``); every other step carries none.
    ``store`` defaults to ``<run>/execution``, read only for a consumer step."""

    def hook(binding: "OwnerBinding", spec: "StepSpec") -> tuple[UntrustedItem, ...]:
        if (binding.module_id, binding.step_id) == (MODULE_ID, RESEARCH_STEP):
            return _evidence_items(research)
        if binding.module_id not in CONSUMERS:
            return ()
        held = Execution(research.parent / "execution") if store is None else store
        attempt = next((a for a in held.read().attempts if a.ticket_id == binding.ticket_id), None)
        if attempt is None:
            raise PromptError(f"no attempt for ticket {binding.ticket_id}")
        return dossier_item(held, attempt, research)

    return hook


def _rejected(path: Path) -> tuple[RefusedItem, ...]:
    """``research/rejected.json`` back into the refused items the dossier lists."""
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        return tuple(
            RefusedItem(
                locator=str(row["locator"]),
                family=str(row["family"]),
                published=None
                if row["published"] is None
                else date.fromisoformat(row["published"]),
                reason=str(row["reason"]),
            )
            for row in rows
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise record.EvidenceRecordInvalid(f"{path.name} cannot be read") from error


def dossier_input(store: Execution, head: Head, research: Path) -> DossierInput:
    """What ``render_dossier`` takes, from the settled CP-DR head (O7-R10): its facts and tables as
    settled, the locked brief read back from ``research/brief.json`` against the head's
    ``research-brief`` input, the evidence record and the refused items. The head's own hash is
    recorded, not compared."""
    if head.module_id != MODULE_ID or head.status == "blocked":
        raise WorkflowError("identity_mismatch")
    module = store.head_module(head)
    bound = next((i.sha256 for i in module.inputs if i.input_id == RESEARCH_BRIEF_INPUT), None)
    attempt = next(
        (a for a in store.read().attempts if a.result_sha256 == head.result_sha256), None
    )
    step = None if attempt is None else _valid_step(attempt, RESEARCH_STEP)
    if bound is None or step is None or step.output_sha256 is None:
        raise WorkflowError("identity_mismatch")
    if not (research / BRIEF_FILE).exists():
        raise BriefInvalid(NOT_LOCKED)
    brief = load_locked_brief(research / BRIEF_FILE, bound)
    submission = ResearchSubmission.model_validate_json(store.step_output(step.output_sha256))
    composed = Composed(module.facts, module.tables, module.claims, module.limitations)
    return tables_dossier_input(
        composed,
        brief,
        claim_states(submission, brief),
        _items(record.read_evidence(research / record.EVIDENCE_FILE)),
        _rejected(research / record.REJECTED_FILE),
        head.result_sha256,
        bound,
    )
