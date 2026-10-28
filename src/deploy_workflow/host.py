"""Task0 v1 single-writer source host; no submission validation or settlement."""

import json
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any, cast
from uuid import uuid4

from deploy_vii.contracts import Input, Module
from deploy_vii.cp1_quality import cp1_quality_inputs
from deploy_vii.cp1_workflow import (
    CP1_PROMOTION,
    PROMOTED,
    CP1Handoff,
    cp1_registers,
    promote_cp1,
    validate_cp1_stage,
)
from deploy_vii.envelope import Envelope, envelope_issues, read_envelope, write_envelope
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepSubmission,
    StepValidation,
    bounded_issues,
    current_inputs,
    head_of,
    settle,
    text_sha256,
)
from deploy_vii.live.context import declared_sources, readable_sources
from deploy_vii.live.prompts import PromptError
from deploy_vii.preparation import PreparedPack
from deploy_vii.quality import QualityReview, assess_quality
from deploy_vii.readiness import ReadinessReview, build_readiness
from deploy_vii.registry import step_chain
from deploy_workflow.tools.source import SourceError, SourceTools

_SOURCE_STEPS = {
    "CP-0": ("source_readiness",),
    "CP-1": ("source_context", "financials"),
    "CP-4": ("legal_covenants",),
}


def _detached(value: dict[str, Any]) -> dict[str, Any]:
    """Copy a JSON value without deepcopy's extra Python frames per nested object."""
    return cast(dict[str, Any], json.loads(json.dumps(value, allow_nan=False, ensure_ascii=False)))


def _step_inputs(attempt: Attempt, preceding: tuple[Any, ...]) -> tuple[Input, ...]:
    return (
        *attempt.inputs,
        *(Input(input_id="step:" + step.step_id, sha256=step.content_hash()) for step in preceding),
    )


def _checked_cp1_step(store: Execution, step: StepSubmission, outcome: StepValidation) -> None:
    """Match Execution.submit_step's normalization and the exact retained output bytes."""
    outcome = StepValidation.model_validate_json(outcome.model_dump_json())
    if (
        step.status != ("invalid" if outcome.issues else "valid")
        or step.issues != bounded_issues(outcome.issues)
        or not outcome.retained_as(step)
        or (not outcome.issues and outcome.output is None)
    ):
        raise ValueError("CP1 retained validation differs")
    if step.output_sha256 is not None and store.step_output(step.output_sha256) != outcome.output:
        raise ValueError("CP1 retained output bytes differ")


def _cp1_failed_result(
    store: Execution,
    snapshot: ExecutionSnapshot,
    attempt: Attempt,
    outcome: StepValidation,
) -> Module:
    """Reproduce the core's empty candidate and independently derived failure settlement."""
    if not outcome.issues or attempt.payload_sha256 is None:
        raise ValueError("CP1 failure lacks retained candidate or validation")
    empty = Module(
        run_id=snapshot.run.run_id,
        issuer_id=snapshot.run.issuer_id,
        as_of=snapshot.run.as_of,
        module_id="CP-1",
        inputs=attempt.inputs,
        attempt=attempt.number,
    ).model_dump_json()
    if store.payload(attempt.payload_sha256) != empty:
        raise ValueError("CP1 failure candidate differs from core")
    finished, result = settle(
        snapshot,
        attempt,
        empty,
        lambda _: outcome.issues,
        pack=store.pack(snapshot),
        load=store.head_module,
    )
    if finished != attempt or store.result(attempt.result_sha256 or "") != result:
        raise ValueError("CP1 failure settlement differs")
    return result


class _CP1Verification:
    """Historical public validation view; composition gives it no inherited writer paths.

    Only the retained CP1 attempt is presented as pending. Real bytes remain in the
    original Execution, and finish/submit_step are narrowly scoped pure callbacks.
    """

    def __init__(self, store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        # `_origin` is the real store and is reachable by name (Python cannot hide it). No
        # public CP-1 API (`promote_cp1`, `cp1_registers`) touches it; `__getattr__` refuses
        # every other name, and the facade's own methods only read through it.
        self._origin = store
        self._snapshot = snapshot
        self._attempt = attempt
        self._active = False
        self.candidate: Module | None = None
        self.outcome: StepValidation | None = None
        self.result_module: Module | None = None
        steps = attempt.steps
        if steps and steps[-1].step_id == "quality" and steps[-1].status == "invalid":
            steps = (
                *steps[:-1],
                steps[-1].model_copy(
                    update={
                        "status": "pending",
                        "issues": (),
                        "output_sha256": None,
                    }
                ),
            )
        pending = attempt.model_copy(
            update={
                "status": "pending",
                "issues": (),
                "result_sha256": None,
                "payload_sha256": None if attempt.issues else attempt.payload_sha256,
                "steps": steps,
            }
        )
        self._view = snapshot.model_copy(
            update={
                "attempts": tuple(
                    pending if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
                ),
            }
        )

    def __getattr__(self, _name: str) -> Any:
        raise ValueError("Historical verification has no mutating or export capability")

    def read(self) -> ExecutionSnapshot:
        return self._view

    def pack(self, snapshot: ExecutionSnapshot | None = None) -> PreparedPack:
        if snapshot is not None and snapshot != self._view and snapshot != self._snapshot:
            raise ValueError("Foreign historical snapshot")
        return self._origin.pack(self._snapshot)

    def payload(self, digest: str) -> str:
        return self._origin.payload(digest)

    def step_output(self, digest: str) -> str:
        return self._origin.step_output(digest)

    def result(self, digest: str) -> Module:
        return self._origin.result(digest)

    def head_module(self, head: Head) -> Module:
        return self._origin.head_module(head)

    def replay(self) -> None:
        if self._active or self.result_module is not None:
            raise ValueError("Historical promotion already replayed")
        self._active = True
        try:
            returned = promote_cp1(
                cast(Execution, self),
                self._attempt.ticket_id,
                self.payload(self._attempt.steps[-1].payload_sha256),
            )
            if returned != self._attempt or self.result_module is None:
                raise ValueError("Historical promotion did not settle its retained attempt")
        finally:
            self._active = False

    def finish(
        self,
        ticket_id: str,
        payload: str,
        validator: Callable[[Module], tuple[str, ...]],
        *,
        interruption: str | None = None,
        qualification: Qualification | None = None,
    ) -> Attempt:
        attempt = self._attempt
        if (
            not self._active
            or self.result_module is not None
            or attempt.issues
            or ticket_id != attempt.ticket_id
            or interruption is not None
            or qualification != PROMOTED
            or attempt.payload_sha256 is None
            or payload != self.payload(attempt.payload_sha256)
        ):
            raise ValueError("Unexpected historical finish callback")
        candidate = Module.model_validate_json(payload)
        finished, result = settle(
            self._snapshot,
            attempt,
            payload,
            validator,
            pack=self.pack(),
            load=self.head_module,
        )
        if finished != attempt or result != self.result(attempt.result_sha256 or ""):
            raise ValueError("CP1 promoted settlement differs")
        self.candidate, self.result_module = candidate, result
        return finished

    def submit_step(
        self,
        ticket_id: str,
        module_id: str,
        sequence: tuple[str, ...],
        step_id: str,
        payload: str,
        validator: Callable[[PreparedPack, Attempt], StepValidation],
    ) -> Attempt:
        attempt = self._attempt
        retained = attempt.steps[-1]
        if (
            not self._active
            or self.result_module is not None
            or ticket_id != attempt.ticket_id
            or module_id != "CP-1"
            or sequence != CP1_PROMOTION
            or step_id != "quality"
            or retained.step_id != "quality"
            or retained.status != "invalid"
            or payload != self.payload(retained.payload_sha256)
        ):
            raise ValueError("Unexpected historical quality callback")
        pending = next(a for a in self._view.attempts if a.ticket_id == ticket_id)
        outcome = validator(self.pack(), pending)
        _checked_cp1_step(self._origin, retained, outcome)
        self.result_module = _cp1_failed_result(self._origin, self._snapshot, attempt, outcome)
        self.outcome = outcome
        return attempt


def _cp1_history(
    store: Execution,
    snapshot: ExecutionSnapshot,
    attempt: Attempt,
) -> StepValidation | None:
    """Authenticate ordered prefixes and every retained invalid within-attempt repair."""
    chain = step_chain("CP-1")
    steps = attempt.steps
    if (
        not steps
        or tuple(s.step_id for s in steps) != chain.steps[: len(steps)]
        or len(steps) > len(chain.steps)
    ):
        raise ValueError("CP1 retained chain differs")
    repair_indices = [
        chain.steps.index(s.step_id) for s in attempt.step_repairs if s.step_id in chain.repairable
    ]
    if len(repair_indices) != len(attempt.step_repairs) or repair_indices != sorted(
        set(repair_indices)
    ):
        raise ValueError("CP1 repair order differs")
    pack = store.pack(snapshot)
    for repair in attempt.step_repairs:
        index = chain.steps.index(repair.step_id)
        if index >= len(steps) or repair.inputs != _step_inputs(attempt, steps[:index]):
            raise ValueError("CP1 repair prefix differs")
        store.payload(repair.payload_sha256)
        replay = attempt.model_copy(update={"steps": (*steps[:index], repair)})
        _checked_cp1_step(store, repair, validate_cp1_stage(store, pack, replay))
    invalid = None
    for index, step in enumerate(steps):
        if step.inputs != _step_inputs(attempt, steps[:index]) or step.status not in (
            "valid",
            "invalid",
        ):
            raise ValueError("CP1 step prefix differs")
        if step.status == "invalid" and index != len(steps) - 1:
            raise ValueError("CP1 invalid stage is not final")
        store.payload(step.payload_sha256)
        if step.output_sha256 is not None:
            store.step_output(step.output_sha256)
        if step.step_id == "quality":
            continue  # promote_cp1 rederives its exact public quality callback below.
        replay = attempt.model_copy(update={"steps": steps[: index + 1]})
        outcome = validate_cp1_stage(store, pack, replay)
        _checked_cp1_step(store, step, outcome)
        if step.status == "invalid":
            if step.step_id in chain.repairable and step.step_id not in {
                r.step_id for r in attempt.step_repairs
            }:
                raise ValueError("CP1 invalid repairable stage has no first rejection")
            invalid = outcome
    return invalid


def _verify_cp1_attempt(
    store: Execution,
    snapshot: ExecutionSnapshot,
    attempt: Attempt,
    producer: Module,
) -> None:
    """Re-enter existing public CP1 promotion or its exact retained core failure route."""
    run = snapshot.run
    if (
        attempt.module_id != "CP-1"
        or attempt.status != "finished"
        or attempt.interruption is not None
        or attempt.number != producer.attempt
        or attempt.result_sha256 != producer.content_hash()
        or attempt.inputs != current_inputs(snapshot, "CP-1")
        or len({i.input_id for i in attempt.inputs}) != len(attempt.inputs)
        or (producer.run_id, producer.issuer_id, producer.as_of, producer.method_version)
        != (run.run_id, run.issuer_id, run.as_of, run.method_version)
    ):
        raise ValueError("CP1 finished identity differs")
    related = tuple(
        a for a in snapshot.attempts if a.module_id == "CP-1" and a.inputs == attempt.inputs
    )
    if attempt.number == 0:
        if (
            attempt.repair_of is not None
            or attempt.repair_issues
            or not related
            or related[0] != attempt
        ):
            raise ValueError("CP1 first attempt ancestry differs")
    else:
        previous = [a for a in snapshot.attempts if a.ticket_id == attempt.repair_of]
        if (
            len(previous) != 1
            or len(related) != 2
            or related != (previous[0], attempt)
            or previous[0].number != 0
            or not previous[0].issues
            or attempt.repair_issues != previous[0].issues
        ):
            raise ValueError("CP1 repair ancestry differs")
        prior = store.result(previous[0].result_sha256 or "")
        if prior.status != "rejected":
            raise ValueError("CP1 repair predecessor is not rejected")
        _verify_cp1_attempt(store, snapshot, previous[0], prior)
    invalid = _cp1_history(store, snapshot, attempt)
    if attempt.issues:
        if (
            producer.status != ("rejected" if attempt.number == 0 else "blocked")
            or attempt.steps[-1].status != "invalid"
        ):
            raise ValueError("CP1 failure status differs")
        if attempt.steps[-1].step_id == "quality":
            probe = _CP1Verification(store, snapshot, attempt)
            probe.replay()
            if probe.result_module != producer:
                raise ValueError("CP1 quality failure differs")
        elif invalid is None or _cp1_failed_result(store, snapshot, attempt, invalid) != producer:
            raise ValueError("CP1 retained failure differs")
        return
    if (
        producer.status not in ("accepted", "restricted")
        or tuple(s.step_id for s in attempt.steps) != CP1_PROMOTION
        or any(s.status != "valid" for s in attempt.steps)
    ):
        raise ValueError("CP1 producer is not promoted")
    probe = _CP1Verification(store, snapshot, attempt)
    registers = cp1_registers(cast(Execution, probe), attempt.ticket_id)
    tail = registers.module.inputs
    expected = (*attempt.inputs, *tail)
    if (
        tuple(i.input_id for i in tail)
        != ("pack", "financial-review", "downstream-report", "statement-history")
        or any(i.status != "accepted" for i in tail)
        or producer.inputs != expected
        or len({i.input_id for i in expected}) != len(expected)
    ):
        raise ValueError("CP1 canonical provenance differs")
    probe.replay()
    handoff = CP1Handoff.model_validate_json(
        store.step_output(attempt.steps[-1].output_sha256 or "")
    )
    quality = assess_quality(
        cp1_quality_inputs(registers),
        QualityReview.model_validate_json(store.payload(attempt.steps[-1].payload_sha256)),
    )
    ledger = registers.downstream.inputs.narrative.inputs.ledger
    if (
        probe.candidate is None
        or probe.result_module != producer
        or handoff.registers_sha256 != registers.content_hash()
        or handoff.quality != quality
        or quality.confidence.qa_status == "Blocked"
        or handoff.gap_limitations != ledger.limitations
        or handoff.candidate_sha256 != probe.candidate.content_hash()
    ):
        raise ValueError("CP1 handoff differs")
    envelope = Envelope(
        run=run,
        module=probe.candidate,
        registers_sha256=registers.content_hash(),
        gap_limitations=ledger.limitations,
        quality=quality,
        journal=attempt.inputs,
    )
    markdown, sidecar = write_envelope(envelope)
    if (
        text_sha256(markdown) != handoff.envelope_sha256
        or text_sha256(sidecar) != handoff.sidecar_sha256
        or envelope_issues(markdown, sidecar)
        or read_envelope(markdown, sidecar) != envelope
    ):
        raise ValueError("CP1 envelope differs")


# In-process parse cache, never persisted. Key: a blob's SHA-256. Every `result`/`pack` call below
# still re-reads the blob and checks its bytes against that digest (`Execution._load`), so a
# missing (SH-R12) or tampered (SH-R16) blob refuses exactly as before; only the pydantic parse
# of bytes already proven identical to a previously parsed and canonical-hash-checked blob is
# skipped. The cached models are frozen with tuple fields. No store or writer handle is cached.
# ponytail: the ceiling is an entry count, not bytes: 4 entries is one history's working set, and a
# cached CP-1 result can keep ~200 MiB alive (44 MB blob), so the worst case is ~800 MiB. Upgrade
# path if that matters: cap by the summed blob size instead of the entry count.
_PARSED_LIMIT = 4
_PARSED_LOCK = Lock()
_PARSED_MODULES: dict[str, Module] = {}
_PARSED_PACKS: dict[str, PreparedPack] = {}


def _remember(cache: dict[str, Any], digest: str, value: Any) -> None:
    with _PARSED_LOCK:
        while len(cache) >= _PARSED_LIMIT:
            del cache[next(iter(cache))]
        cache[digest] = value


class _ParsedExecution(Execution):
    """Same store directory; `result` and `pack` skip re-parsing blobs proven byte-identical."""

    def result(self, sha256: str) -> Module:
        raw = self._load(sha256)  # reads and hash-checks the bytes on every call
        with _PARSED_LOCK:
            cached = _PARSED_MODULES.get(sha256)
        if cached is not None:
            return cached
        module = Module.model_validate_json(raw)
        if module.content_hash() != sha256:
            raise ValueError("Execution result blob is not the canonical module")
        _remember(_PARSED_MODULES, sha256, module)
        return module

    def pack(self, snapshot: ExecutionSnapshot | None = None) -> PreparedPack:
        snapshot = self.read() if snapshot is None else snapshot
        raw = self._load(snapshot.pack_sha256)
        with _PARSED_LOCK:
            pack = _PARSED_PACKS.get(snapshot.pack_sha256)
        if pack is None:
            pack = PreparedPack.model_validate_json(raw)
            if pack.content_hash() != snapshot.pack_sha256:
                raise ValueError("Execution pack blob is not the canonical pack of this snapshot")
            _remember(_PARSED_PACKS, snapshot.pack_sha256, pack)
        if pack.run != snapshot.run:
            raise ValueError("Execution pack blob is not the canonical pack of this snapshot")
        return pack


class _RecordingExecution(_ParsedExecution):
    """Same store directory; remembers every blob digest read (and hash-checked) through it."""

    def __init__(self, directory: Path) -> None:
        super().__init__(directory)
        self.touched: set[str] = set()

    def _load(self, sha256: str) -> bytes:
        raw = super()._load(sha256)
        self.touched.add(sha256)
        return raw


# In-process only, never persisted. Key: (snapshot content hash, producer result hash). Value:
# the blob digests the full verification read. A hit re-reads and hash-checks each of them, so
# tampered (SH-R16) or missing (SH-R12) bytes still refuse; a different snapshot always misses.
# No store or writer handle is cached.
_CP1_VERIFIED: dict[tuple[str, str], frozenset[str]] = {}
_CP1_VERIFIED_LIMIT = 16
_CP1_VERIFIED_LOCK = Lock()


def _verify_cp1_attempt_memoised(
    store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt, producer: Module
) -> None:
    key = (sha256(snapshot.model_dump_json().encode()).hexdigest(), producer.content_hash())
    with _CP1_VERIFIED_LOCK:
        touched = _CP1_VERIFIED.get(key)
    if touched is not None:
        for digest in sorted(touched):
            store._load(digest)  # raises ValueError for missing or tampered bytes
        return
    recorder = _RecordingExecution(store.directory)
    _verify_cp1_attempt(recorder, snapshot, attempt, producer)
    with _CP1_VERIFIED_LOCK:
        while len(_CP1_VERIFIED) >= _CP1_VERIFIED_LIMIT:
            del _CP1_VERIFIED[next(iter(_CP1_VERIFIED))]
        _CP1_VERIFIED[key] = frozenset(recorder.touched)


def _cp1_producer_inputs(store: Execution, snapshot: ExecutionSnapshot, producer: Module) -> bool:
    produced = producer.content_hash()
    selected = [
        a for a in snapshot.attempts if a.module_id == "CP-1" and a.result_sha256 == produced
    ]
    if len(selected) != 1:
        return False
    _verify_cp1_attempt_memoised(store, snapshot, selected[0], producer)
    qualification = PROMOTED if producer.status in ("accepted", "restricted") else None
    return tuple(h for h in snapshot.heads if h.module_id == "CP-1") == (
        head_of(producer, qualification),
    )


def _producer_inputs(store: Execution, snapshot: ExecutionSnapshot, producer: Module) -> bool:
    """Authenticate CP0 canonical readiness and CP1's actual promotion/failure history."""
    expected = current_inputs(snapshot, producer.module_id)
    if producer.module_id == "CP-1":
        return _cp1_producer_inputs(store, snapshot, producer)
    if producer.module_id != "CP-0":
        return producer.inputs == expected
    selected = [
        a
        for a in snapshot.attempts
        if a.module_id == "CP-0" and a.result_sha256 == producer.content_hash()
    ]
    if len(selected) != 1:
        return False
    attempt = selected[0]
    if (
        attempt.status != "finished"
        or attempt.issues
        or attempt.interruption is not None
        or attempt.number != producer.attempt
        or attempt.inputs != expected
    ):
        return False
    if not attempt.steps:
        # A removed review step must not hide provenance still held in its candidate.
        if attempt.payload_sha256 is None or producer.inputs != expected:
            return False
        candidate_json = store.payload(attempt.payload_sha256)
        candidate = Module.model_validate_json(candidate_json)
        if candidate.inputs != expected:
            return False
        finished, result = settle(
            snapshot,
            attempt,
            candidate_json,
            lambda _: (),
            pack=store.pack(snapshot),
            load=store.head_module,
        )
        return finished == attempt and result == producer
    if len(attempt.steps) != 1:
        return False
    step = attempt.steps[0]
    if (
        step.step_id != "source_readiness"
        or step.status != "valid"
        or step.inputs != expected
        or step.output_sha256 is None
        or attempt.payload_sha256 is None
    ):
        return False
    review = ReadinessReview.model_validate_json(store.payload(step.payload_sha256))
    if producer.inputs != (
        *expected,
        Input(input_id="readiness-review", sha256=review.content_hash()),
    ):
        return False
    pack = store.pack(snapshot)
    candidate = build_readiness(pack, review, attempt=attempt.number)
    candidate_json = candidate.model_dump_json()
    if (
        step.output_sha256 != candidate.content_hash()
        or store.step_output(step.output_sha256) != candidate_json
        or store.payload(attempt.payload_sha256) != candidate_json
    ):
        return False
    finished, result = settle(
        snapshot,
        attempt,
        candidate_json,
        lambda supplied: () if supplied == candidate else ("CP0 candidate differs",),
        pack=pack,
        load=store.head_module,
    )
    return finished == attempt and result == producer


def _execution_state(
    store: Execution,
    ticket_id: str,
    step_id: str,
) -> tuple[ExecutionSnapshot, Attempt, PreparedPack, tuple[str, ...]]:
    """Check authority and every selected blob before exposing any source capability."""
    try:
        # Only an exact Execution is swapped: a subclass (e.g. a read()-pinned historical view)
        # keeps its own reads, and then the pack hash is checked explicitly below.
        # ponytail: an exact Execution is swapped for the cached store, so instance or class patches
        # on it are bypassed (the authentic on-disk state is read); check vars(store) if a caller
        # ever patches one.
        substituted = type(store) is Execution
        if substituted:
            store = _ParsedExecution(store.directory)
        snapshot = store.read()
        tickets = [a for a in snapshot.attempts if a.ticket_id == ticket_id]
        if len(tickets) != 1:
            raise SourceError("not_permitted")
        attempt = tickets[0]
        pending = (
            attempt.status == "pending"
            and attempt.payload_sha256 is None
            and attempt.result_sha256 is None
            and attempt.interruption is None
            and not attempt.issues
        )
        if not pending:
            raise SourceError("not_permitted")
        if step_id not in _SOURCE_STEPS.get(attempt.module_id, ()):
            raise SourceError("not_permitted")
        chain = step_chain(attempt.module_id)
        if step_id not in chain.pack_sources:
            raise SourceError("not_permitted")
        prior_steps = attempt.steps
        ordered_prefix = tuple(s.step_id for s in prior_steps) == chain.steps[: len(prior_steps)]
        all_valid = all(s.status == "valid" for s in prior_steps)
        if (
            not all_valid
            or not ordered_prefix
            or len(prior_steps) >= len(chain.steps)
            or chain.steps[len(prior_steps)] != step_id
        ):
            raise SourceError("not_permitted")
        if sum(a.status == "pending" for a in snapshot.attempts) != 1:
            raise SourceError("identity_mismatch")
        if current_inputs(snapshot, attempt.module_id) != attempt.inputs:
            raise SourceError("identity_mismatch")
        if len({i.input_id for i in attempt.inputs}) != len(attempt.inputs):
            raise SourceError("identity_mismatch")
        pack = store.pack(snapshot)  # re-read, hash-checked and canonical for this snapshot
        if not substituted and pack.content_hash() != snapshot.pack_sha256:
            raise SourceError("identity_mismatch")
        if pack.run != snapshot.run:
            raise SourceError("identity_mismatch")
        heads = {h.module_id: h for h in snapshot.heads}
        if len(heads) != len(snapshot.heads):
            raise SourceError("identity_mismatch")
        run = snapshot.run
        for bound in attempt.inputs:
            if bound.input_id == "prepared-pack":
                if bound.sha256 != snapshot.pack_sha256 or bound.status != "accepted":
                    raise SourceError("identity_mismatch")
                continue
            head = heads[bound.input_id]
            producer = store.head_module(head)
            same_head = (head.result_sha256, head.status) == (bound.sha256, bound.status)
            same_run = (
                producer.run_id,
                producer.issuer_id,
                producer.as_of,
                producer.method_version,
            ) == (run.run_id, run.issuer_id, run.as_of, run.method_version)
            if not same_head or not same_run or not _producer_inputs(store, snapshot, producer):
                raise SourceError("identity_mismatch")
        for index, step in enumerate(prior_steps):
            if step.inputs != _step_inputs(attempt, prior_steps[:index]):
                raise SourceError("identity_mismatch")
            if step.output_sha256 is None:
                raise SourceError("identity_mismatch")
            store.payload(step.payload_sha256)
            store.step_output(step.output_sha256)
        for repair in attempt.step_repairs:
            if repair.step_id not in chain.repairable:
                raise SourceError("not_permitted")
            index = chain.steps.index(repair.step_id)
            if index > len(prior_steps):
                raise SourceError("not_permitted")
            if repair.inputs != _step_inputs(attempt, prior_steps[:index]):
                raise SourceError("identity_mismatch")
            store.payload(repair.payload_sha256)
            if repair.output_sha256 is not None:
                store.step_output(repair.output_sha256)
        if attempt.number == 0:
            if attempt.repair_of is not None:
                raise SourceError("identity_mismatch")
        else:
            previous = [a for a in snapshot.attempts if a.ticket_id == attempt.repair_of]
            if (
                len(previous) != 1
                or previous[0].status != "finished"
                or not previous[0].issues
                or previous[0].module_id != attempt.module_id
                or previous[0].number != 0
                or previous[0].inputs != attempt.inputs
                or (attempt.module_id == "CP-4" and attempt.repair_issues != previous[0].issues)
            ):
                raise SourceError("identity_mismatch")
        ids = tuple(s.source_id for s in pack.sources)
        declared = set(declared_sources(store, attempt, step_id, ids))
        readable = set(readable_sources(store, attempt, step_id))
        if not declared <= set(ids) or not readable <= set(ids):
            raise SourceError("identity_mismatch")
        sources = tuple(ident for ident in ids if ident in declared and ident in readable)
        if attempt.module_id == "CP-4" and not sources:
            raise SourceError("not_permitted")
        if store.read().content_hash() != snapshot.content_hash():
            raise SourceError("stale_binding")
        return snapshot, attempt, pack, sources
    except SourceError:
        raise
    except (ValueError, KeyError, OSError):
        raise SourceError("identity_mismatch") from None


def _json_arguments(arguments: Any) -> dict[str, Any]:
    """JSON input must round-trip without coercing tuples, keys or numeric sentinels."""

    def check(value: Any) -> None:
        if type(value) in (str, int, float, bool, type(None)):
            return
        if type(value) is list:
            for item in value:
                check(item)
            return
        if type(value) is dict and all(type(key) is str for key in value):
            for item in value.values():
                check(item)
            return
        raise ValueError("not JSON")

    if type(arguments) is not dict:
        raise ValueError("arguments must be an object")
    check(arguments)
    return _detached(arguments)


class SourceSession:
    """Trusted factory pins authority; analytical callers can only invoke or bind bytes."""

    def __init__(
        self,
        store: Execution,
        snapshot: ExecutionSnapshot,
        attempt: Attempt,
        step_id: str,
        pack: PreparedPack,
        sources: tuple[str, ...],
    ) -> None:
        self._store = store
        self._ticket_id = attempt.ticket_id
        self._step_id = step_id
        self._snapshot_sha256 = snapshot.content_hash()
        run = snapshot.run
        self._binding = {
            "run_id": run.run_id,
            "issuer_id": run.issuer_id,
            "as_of": run.as_of.isoformat(),
            "method_version": run.method_version,
            "pack_sha256": pack.content_hash(),
            "snapshot_sha256": self._snapshot_sha256,
            "module_id": attempt.module_id,
            "step_id": step_id,
            "ticket_id": attempt.ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
        }
        self._tools = SourceTools(pack, sources, extraction=step_id == "financials")
        self._operation = Lock()
        self._records_lock = Lock()
        self._sequence = 0
        self._calls: dict[int, dict[str, Any]] = {}

    @classmethod
    def from_execution(cls, store: Execution, ticket_id: str, step_id: str) -> "SourceSession":
        snapshot, attempt, pack, sources = _execution_state(store, ticket_id, step_id)
        return cls(store, snapshot, attempt, step_id, pack, sources)

    def _assert_current(self) -> None:
        try:
            if self._store.read().content_hash() != self._snapshot_sha256:
                raise SourceError("stale_binding")
            snapshot, _, _, _ = _execution_state(self._store, self._ticket_id, self._step_id)
            if snapshot.content_hash() != self._snapshot_sha256:
                raise SourceError("stale_binding")
        except SourceError:
            raise
        except (ValueError, OSError):
            raise SourceError("identity_mismatch") from None

    def _receipt(
        self,
        sequence: int,
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        status: str,
        body: str | None,
        code: str | None,
    ) -> dict[str, Any]:
        receipt = {
            "schema_version": "tool-receipt/1",
            "call_id": call_id,
            "sequence": sequence,
            "binding": _detached(self._binding),
            "tool": name,
            "arguments": arguments,
            "status": status,
            "body": body,
            "error_code": code,
            "source_evidence": self._tools.evidence(),
        }
        with self._records_lock:
            self._calls[sequence] = _detached(receipt)
        return _detached(receipt)

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._records_lock:
            self._sequence += 1
            sequence = self._sequence
        call_id = str(uuid4())
        name = tool_name if type(tool_name) is str else ""
        try:
            copied = _json_arguments(arguments)
        except (ValueError, TypeError, RecursionError):
            return self._receipt(sequence, call_id, name, {}, "refused", None, "bad_arguments")
        if not self._operation.acquire(blocking=False):
            return self._receipt(sequence, call_id, name, copied, "refused", None, "not_permitted")
        try:
            self._assert_current()
            body, staged = self._tools.stage(name, copied)
            self._assert_current()
            self._tools.commit(staged)
            return self._receipt(sequence, call_id, name, copied, "ok", body, None)
        except SourceError as error:
            return self._receipt(sequence, call_id, name, copied, "refused", None, error.code)
        except PromptError:
            return self._receipt(sequence, call_id, name, copied, "refused", None, "render_refused")
        except Exception:  # noqa: BLE001 - Task0 requires sanitized unexpected local errors.
            return self._receipt(sequence, call_id, name, copied, "error", None, "internal_error")
        finally:
            self._operation.release()

    def bind_submission(self, payload: str) -> dict[str, Any]:
        if not self._operation.acquire(blocking=False):
            raise SourceError("not_permitted")
        try:
            self._assert_current()
            if type(payload) is not str:
                raise SourceError("bad_arguments")
            try:
                digest = sha256(payload.encode("utf-8")).hexdigest()
            except UnicodeError:
                raise SourceError("bad_arguments") from None
            with self._records_lock:
                calls = [self._calls[index] for index in sorted(self._calls)]
                record = {
                    "schema_version": "submission-binding/1",
                    "binding": _detached(self._binding),
                    "payload_sha256": digest,
                    "successful_call_ids": [c["call_id"] for c in calls if c["status"] == "ok"],
                    "call_ids": [c["call_id"] for c in calls],
                    "source_evidence": self._tools.evidence(),
                }
            self._assert_current()
            return record
        finally:
            self._operation.release()
