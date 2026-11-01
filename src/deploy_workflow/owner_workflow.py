"""Plan-driven offline owner workflow: one adapter for every declared owner spec.

Execution and the adopted owner cores own every calculation and settlement. This
adapter owns finite capabilities, immutable participation evidence and the receipt.
It generalises `financial_workflow` (which stays the reference and is imported, never
edited): the walk follows `registry.plan`, each module's steps come from a declared
`OwnerSpec`, and paths are supplied by trusted setup, never by a message.
G1 shipped CP-0, CP-1 and CP-MODEL; S1a adds CP-1A and CP-2 and Stage 2 adds CP-4 (their
probes and views live in `deploy_workflow.owners`). G1-X
(`docs/G1X-OWNER-CORE-PROTOCOL.md`) serves owner cores: an owner-only module (no live step
contract) is entered through its registered core (`_CORES`), any module may register a
precheck gate (`_PRECHECKS`), and every module with a `_VIEWS` entry may be read through
`module_context` or `step_context`. `OwnerWorkflow.open` resumes a killed run from the retained
audit (G5b); its docstring says how the journal and the audit are reconciled and what it cannot
resume.
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Lock
from types import MappingProxyType, ModuleType
from typing import Annotated, Any, Literal, TextIO
from uuid import uuid4

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer

from deploy_vii.business_context import PROMOTED as CP1A_PROMOTED
from deploy_vii.contracts import Contract, Hash, Identifier, Input, Module, Run
from deploy_vii.cp0_workflow import _validate_review as cp0_validate_review
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.cp1_workflow import PROMOTED, _quality_stage, validate_cp1_stage
from deploy_vii.cp2_synthesis import PROMOTED as CP2_PROMOTED
from deploy_vii.cp4_legal import PROMOTED as CP4_PROMOTED
from deploy_vii.cp5_integrity import PROMOTED as CP5_PROMOTED
from deploy_vii.cp_model_workflow import (
    PUBLISHED,
    CpModelRefused,
    publish_cp_model,
    verify_cp_model_publication,
)
from deploy_vii.execution import (
    MAX_INTERRUPTION_CHARS,
    WITHIN_ATTEMPT_REPAIR,
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    NotAuthorized,
    StepSubmission,
    StepValidation,
    bounded_issues,
    current_inputs,
    head_of,
    settle,
    shortened,
    text_sha256,
)
from deploy_vii.live.schema import normalise
from deploy_vii.live.submission import (
    PREFILLED,
    STEPS,
    Submitted,
    _validate_prefilled,
    known_bindings,
    prefill,
    submit_model_payload,
)
from deploy_vii.live.tools import ToolRules
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import StepChain, dependencies, edge_rule, plan, step_chain
from deploy_workflow import host
from deploy_workflow.financial_workflow import (
    FILES,
    MAX_CALLS,
    MAX_LINE,
    MAX_MESSAGES,
    FinancialBinding,
    ModelPublication,
    PublicationCall,
    _evidence_issues,
    _files,
    _filled,
    _FrozenExecution,
    _hash,
    _historical,
    _nonfinite_json,
    _parse,
    _projection,
    _put,
    _record,
    _snapshot,
    _verify_cp0,
    _verify_model_settlement,
    _verify_promotion,
)
from deploy_workflow.host import SourceSession
from deploy_workflow.owners import (
    cp1a,
    cp1b,
    cp1c,
    cp1d,
    cp2,
    cp2a,
    cp2d,
    cp2e,
    cp2g,
    cp2h,
    cp3,
    cp3c,
    cp3d,
    cp4,
    cp4c,
    cp5,
    cp6,
    cp8,
    cpdr,
    cpl10,
)
from deploy_workflow.tools.source import SourceError
from deploy_workflow.workflow import SourceEvidence, WorkflowError

AUDIT = "owner-run-audit"
SUPPORTED_ANALYTICAL = frozenset(
    {
        "CP-0",
        "CP-1",
        "CP-1A",
        "CP-1B",
        "CP-2",
        "CP-3D",
        "CP-DR",
        "CP-2E",
        "CP-3",
        "CP-5",
        "CP-8",
        "CP-2A",
        "CP-2D",
        "CP-4",
        "CP-L10",
        "CP-1D",
        "CP-2G",
        "CP-1C",
        "CP-3C",
        "CP-2H",
        "CP-4C",
        "CP-6",
    }
)
BLOCKED_EDGE = "Required upstream is unrun, stale or blocked"
# G1-X §2: the fixed owner-core registry, one row per owner-only module (`_owner_only`: no
# registered `registry.step_chain`, or one whose `shared_live` is false). Never caller-supplied; module tasks add their rows. A core
# supplies `STEP_IDS`, `SCHEMAS`, `submit` and, for steps with pack sources, `RULES`.
_CORES: dict[str, ModuleType] = {
    "CP-DR": cpdr,
    "CP-3D": cp3d,
    "CP-2E": cp2e,
    "CP-8": cp8,
    "CP-2A": cp2a,
    "CP-2D": cp2d,
    "CP-L10": cpl10,
    "CP-1D": cp1d,
    "CP-2G": cp2g,
    "CP-1C": cp1c,
    "CP-3C": cp3c,
    "CP-2H": cp2h,
    "CP-4C": cp4c,
    "CP-1B": cp1b,
}
_QUALIFICATION = {
    "CP-1": PROMOTED,
    "CP-1A": CP1A_PROMOTED,
    "CP-2": CP2_PROMOTED,
    "CP-MODEL": PUBLISHED,
    "CP-DR": cpdr.QUALIFICATION,
    "CP-3D": cp3d.QUALIFICATION,
    "CP-2E": cp2e.QUALIFICATION,
    "CP-3": cp3.QUALIFICATION,
    "CP-5": CP5_PROMOTED,
    "CP-8": cp8.QUALIFICATION,
    "CP-2A": cp2a.QUALIFICATION,
    "CP-2D": cp2d.QUALIFICATION,
    "CP-4": CP4_PROMOTED,
    "CP-L10": cpl10.QUALIFICATION,
    "CP-1D": cp1d.QUALIFICATION,
    "CP-2G": cp2g.QUALIFICATION,
    "CP-1C": cp1c.QUALIFICATION,
    "CP-3C": cp3c.QUALIFICATION,
    "CP-2H": cp2h.QUALIFICATION,
    "CP-4C": cp4c.QUALIFICATION,
    "CP-6": cp6.QUALIFICATION,
    "CP-1B": cp1b.QUALIFICATION,
}
_PROBES: dict[str, Callable[[Execution, ExecutionSnapshot, Attempt], None]] = {
    "CP-0": _verify_cp0,
    "CP-1": _verify_promotion,
    "CP-1A": cp1a.probe,
    "CP-2": cp2.probe,
    "CP-DR": cpdr.probe,
    "CP-3D": cp3d.probe,
    "CP-2E": cp2e.probe,
    "CP-3": cp3.probe,
    "CP-5": cp5.probe,
    "CP-8": cp8.probe,
    "CP-2A": cp2a.probe,
    "CP-2D": cp2d.probe,
    "CP-4": cp4.probe,
    "CP-L10": cpl10.probe,
    "CP-1D": cp1d.probe,
    "CP-2G": cp2g.probe,
    "CP-1C": cp1c.probe,
    "CP-3C": cp3c.probe,
    "CP-2H": cp2h.probe,
    "CP-4C": cp4c.probe,
    "CP-6": cp6.probe,
    "CP-1B": cp1b.probe,
}
# The exact `read_inputs` view of each `module_context` or `step_context` step (S1a lease rev 2,
# M4; G1-X §3: any step with an entry here may declare `inputs="module_context"`; CP-4 declares
# `inputs="step_context"`, rulings stage2 Q4). Both are served as
# `_VIEWS[step](historical, attempt)`.
_VIEWS: dict[str, Callable[[Execution, Attempt], tuple[str, str]]] = {
    "credit_synthesis": cp2.view,
    "research": cpdr.view,
    "integrity_review": cp5.view,
    "downside_pathway": cp2a.view,
    "liquidity_bridge": cp2d.view,
    "legal_covenants": cp4.view,
    "change_screen": cpl10.view,
    "earnings_quality": cp1d.view,
    "forward_credit_model": cp2g.view,
    "peer_benchmark": cp1c.view,
    "refinancing_risk": cp3c.view,
    "rating_triggers": cp2h.view,
    "restructuring_fulcrum": cp4c.view,
    "committee_challenge": cp6.view,
    "earnings_delta": cp1b.view,
}
# The validator each module's own entry hands `Execution.submit_step`: the verifier replays an
# invalid step through it at the historical snapshot (S1a R4-2). Module tasks add their rows;
# every analytical module but CP-0 and CP-1 needs one, or create refuses it (G1-X §2).
_ENTRY_VALIDATORS: dict[str, Callable[[Execution, PreparedPack, Attempt], StepValidation]] = {
    "CP-1A": cp1a.ENTRY_VALIDATOR,
    "CP-2": cp2.ENTRY_VALIDATOR,
    "CP-DR": cpdr.ENTRY_VALIDATOR,
    "CP-3D": cp3d.ENTRY_VALIDATOR,
    "CP-2E": cp2e.ENTRY_VALIDATOR,
    "CP-3": cp3.ENTRY_VALIDATOR,
    "CP-5": cp5.ENTRY_VALIDATOR,
    "CP-8": cp8.ENTRY_VALIDATOR,
    "CP-2A": cp2a.ENTRY_VALIDATOR,
    "CP-2D": cp2d.ENTRY_VALIDATOR,
    "CP-4": cp4.ENTRY_VALIDATOR,
    "CP-L10": cpl10.ENTRY_VALIDATOR,
    "CP-1D": cp1d.ENTRY_VALIDATOR,
    "CP-2G": cp2g.ENTRY_VALIDATOR,
    "CP-1C": cp1c.ENTRY_VALIDATOR,
    "CP-3C": cp3c.ENTRY_VALIDATOR,
    "CP-2H": cp2h.ENTRY_VALIDATOR,
    "CP-4C": cp4c.ENTRY_VALIDATOR,
    "CP-6": cp6.ENTRY_VALIDATOR,
    "CP-1B": cp1b.ENTRY_VALIDATOR,
}
# CP-0 and CP-1 keep the reused financial helpers, which are bound to their 11-field binding.
_FINANCIAL_MODULES = frozenset({"CP-0", "CP-1"})


@dataclass(frozen=True)
class StepSpec:
    """One journal step. `sources`: pack tools (SourceSession); `extract`: statement
    extraction is offered; `upstream_grant`: frozen-upstream grant (none yet);
    `inputs`: `projection` lets `read_inputs` return the adopted CP-1 view and
    `module_context` and `step_context` the step's exact view (its `_VIEWS` entry); any
    `inputs` other than `none` must be read before the step is submitted, with or without a
    source session;
    `rules`: `precheck` applies the evidence rules of `financial_workflow._evidence_issues`
    before the journal (a failing submit is refused and writes nothing; CP-0 and CP-1 only);
    `journaled` hands the tool-loop rules to the journal (a failing submit is retained as an
    invalid step): `ToolRules` for a live-contract step, the core's `RULES` for an owner-only
    one. A module's `_PRECHECKS` gate runs before either mode (G1-X §4)."""

    step_id: str
    schema: type[Contract]
    sources: bool
    extract: bool
    upstream_grant: Mapping[str, Any] | None
    inputs: Literal["none", "projection", "module_context", "step_context"]
    rules: Literal["none", "precheck", "journaled"]


@dataclass(frozen=True)
class OwnerSpec:
    module_id: str
    steps: tuple[StepSpec, ...]
    entry: Literal["cp0_review", "model_payload", "owner_core"] | None
    kind: Literal["analytical", "deterministic"]
    publish: Callable[..., Attempt] | None


def _default_specs() -> dict[str, OwnerSpec]:
    from deploy_vii.business_context import BusinessContextSubmission
    from deploy_vii.cp1_workflow import FinancialSubmission
    from deploy_vii.cp2_synthesis import CreditSynthesisSubmission
    from deploy_vii.cp3_relative_value import RelativeValueSubmission
    from deploy_vii.cp4_legal import CovenantInterpretationSubmission
    from deploy_vii.cp5_integrity import IntegritySubmission
    from deploy_vii.cp6_committee import CommitteeSubmission
    from deploy_vii.downstream_readiness import DownstreamReview
    from deploy_vii.narrative import NarrativeReview
    from deploy_vii.quality import QualityReview
    from deploy_vii.readiness import ReadinessReview
    from deploy_vii.source_context import SourceContextReview
    from deploy_workflow.owners.cp2a import DownsideSubmission
    from deploy_workflow.owners.cp2d import LiquidityBridgeSubmission
    from deploy_workflow.owners.cp2e import MacroFxSubmission
    from deploy_workflow.owners.cp8 import DecisionLedgerSubmission
    from deploy_workflow.owners.cpdr import ResearchSubmission
    from deploy_workflow.owners.cpl10 import ChangeScreenSubmission

    def step(
        step_id: str,
        schema: type[Contract],
        *,
        sources: bool = False,
        extract: bool = False,
        inputs: Literal["none", "projection", "module_context", "step_context"] = "none",
        rules: Literal["none", "precheck", "journaled"] = "none",
    ) -> StepSpec:
        return StepSpec(
            step_id=step_id,
            schema=schema,
            sources=sources,
            extract=extract,
            upstream_grant=None,
            inputs=inputs,
            rules=rules,
        )

    return {
        "CP-0": OwnerSpec(
            module_id="CP-0",
            steps=(step("source_readiness", ReadinessReview, sources=True, rules="precheck"),),
            entry="cp0_review",
            kind="analytical",
            publish=None,
        ),
        "CP-1": OwnerSpec(
            module_id="CP-1",
            steps=(
                step("source_context", SourceContextReview, sources=True, rules="precheck"),
                step(
                    "financials",
                    FinancialSubmission,
                    sources=True,
                    extract=True,
                    rules="precheck",
                ),
                step("narrative", NarrativeReview, inputs="projection"),
                step("readiness", DownstreamReview, inputs="projection"),
                step("quality", QualityReview, inputs="projection"),
            ),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-1A": OwnerSpec(
            module_id="CP-1A",
            steps=(
                step(
                    "business_context",
                    BusinessContextSubmission,
                    sources=True,
                    rules="journaled",
                ),
            ),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-2": OwnerSpec(
            module_id="CP-2",
            steps=(step("credit_synthesis", CreditSynthesisSubmission, inputs="module_context"),),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-MODEL": OwnerSpec(
            module_id="CP-MODEL",
            steps=(),
            entry=None,
            kind="deterministic",
            publish=publish_cp_model,
        ),
        # G1-X owner-only module (docs/CPDR-OWNER-LEASE.md Public API): the agenda is its
        # `module_context` view, the pack tools its evidence; every issue is a journaled step.
        "CP-DR": OwnerSpec(
            module_id="CP-DR",
            steps=(
                step(
                    "research",
                    ResearchSubmission,
                    sources=True,
                    inputs="module_context",
                    rules="journaled",
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-3D": OwnerSpec(
            module_id="CP-3D",
            steps=(
                step(
                    "market_implied", cp3d.MarketImpliedSubmission, sources=True, rules="journaled"
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-2E": OwnerSpec(
            module_id="CP-2E",
            steps=(
                step(
                    "macro_fx",
                    MacroFxSubmission,
                    sources=True,
                    rules="journaled",
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-3": OwnerSpec(
            module_id="CP-3",
            steps=(
                step(
                    "relative_value",
                    RelativeValueSubmission,
                    sources=True,
                    rules="journaled",
                ),
            ),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-5": OwnerSpec(
            module_id="CP-5",
            steps=(step("integrity_review", IntegritySubmission, inputs="module_context"),),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-8": OwnerSpec(
            module_id="CP-8",
            steps=(
                step(
                    "decision_ledger",
                    DecisionLedgerSubmission,
                    sources=True,
                    rules="journaled",
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-2A": OwnerSpec(
            module_id="CP-2A",
            steps=(step("downside_pathway", DownsideSubmission, inputs="module_context"),),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-2D": OwnerSpec(
            module_id="CP-2D",
            steps=(step("liquidity_bridge", LiquidityBridgeSubmission, inputs="module_context"),),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-4": OwnerSpec(
            module_id="CP-4",
            steps=(
                step(
                    "legal_covenants",
                    CovenantInterpretationSubmission,
                    sources=True,
                    inputs="step_context",
                    rules="journaled",
                ),
            ),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
        "CP-L10": OwnerSpec(
            module_id="CP-L10",
            steps=(step("change_screen", ChangeScreenSubmission, inputs="module_context"),),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-1D": OwnerSpec(
            module_id="CP-1D",
            steps=(
                step(
                    "earnings_quality",
                    cp1d.EarningsQualitySubmission,
                    sources=True,
                    inputs="module_context",
                    rules="journaled",
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-2G": OwnerSpec(
            module_id="CP-2G",
            steps=(step("forward_credit_model", cp2g.ForwardSubmission, inputs="module_context"),),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        # docs/CP1C-OWNER-LEASE.md Public API: the view is the agenda, the pack tools (identity,
        # financial and, when held, peers) the evidence; every content rule is journaled.
        "CP-1C": OwnerSpec(
            module_id="CP-1C",
            steps=(
                step(
                    "peer_benchmark",
                    cp1c.PeerBenchmarkSubmission,
                    sources=True,
                    inputs="module_context",
                    rules="journaled",
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-3C": OwnerSpec(
            module_id="CP-3C",
            steps=(
                step("refinancing_risk", cp3c.RefinancingRiskSubmission, inputs="module_context"),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-2H": OwnerSpec(
            module_id="CP-2H",
            steps=(
                step(
                    "rating_triggers",
                    cp2h.TriggerSubmission,
                    sources=True,
                    inputs="module_context",
                    rules="journaled",
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-4C": OwnerSpec(
            module_id="CP-4C",
            steps=(
                step(
                    "restructuring_fulcrum",
                    cp4c.RestructuringSubmission,
                    sources=True,
                    inputs="module_context",
                    rules="journaled",
                ),
            ),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-1B": OwnerSpec(
            module_id="CP-1B",
            steps=(step("earnings_delta", cp1b.EarningsDeltaOwnerReview, inputs="module_context"),),
            entry="owner_core",
            kind="analytical",
            publish=None,
        ),
        "CP-6": OwnerSpec(
            module_id="CP-6",
            steps=(step("committee_challenge", CommitteeSubmission, inputs="module_context"),),
            entry="model_payload",
            kind="analytical",
            publish=None,
        ),
    }


OWNER_SPECS: Mapping[str, OwnerSpec] = MappingProxyType(_default_specs())


class OwnerBinding(Contract):
    run_id: Identifier
    issuer_id: Identifier
    as_of: str
    method_version: str
    pack_sha256: Hash
    snapshot_sha256: Hash
    module_id: Identifier
    step_id: Identifier
    ticket_id: Identifier
    attempt: int
    inputs: tuple[Input, ...]


# G1-X §4: a module's optional precheck gate, `precheck(store, binding, stored)` over the filled
# payload. Issues refuse the submission before any rule and before the journal; the verifier
# recomputes it for every submission. Module tasks add their rows (live-contract or owner-only).
_PRECHECKS: dict[str, Callable[[Execution, OwnerBinding, str], tuple[str, ...]]] = {
    "CP-4": cp4.precheck,
}


class OwnerCall(Contract):
    schema_version: Literal["tool-receipt/1"]
    call_id: str
    sequence: int
    binding: OwnerBinding
    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "refused", "error"]
    body: str | None
    error_code: str | None
    source_evidence: SourceEvidence


class OwnerInputRead(Contract):
    binding: OwnerBinding
    sequence: int
    operation: Literal["read_inputs"] = "read_inputs"
    inputs_sha256: Hash
    body: str


class OwnerSubmissionBinding(Contract):
    schema_version: Literal["submission-binding/1"] = "submission-binding/1"
    binding: OwnerBinding
    payload_sha256: Hash
    successful_call_ids: tuple[str, ...]
    call_ids: tuple[str, ...]
    source_evidence: SourceEvidence


class OwnerSubmission(Contract):
    sequence: int
    binding: OwnerSubmissionBinding
    stored_payload_sha256: Hash
    canonical_review_sha256: Hash | None
    disposition: Literal["valid", "invalid", "refused"]
    issues: tuple[str, ...]
    snapshot_after_sha256: Hash
    nulls_resolved: tuple[str, ...] = ()
    prefilled: tuple[str, ...] = ()
    prefilled_kinds: tuple[str, ...] = ()
    step_sha256: Hash | None = None
    step_output_sha256: Hash | None = None


class BeginRecord(Contract):
    module_id: Identifier
    ticket_id: Identifier
    attempt: int
    snapshot_before_sha256: Hash
    snapshot_after_sha256: Hash


class RefusedBegin(Contract):
    """A begin the journal refused: why, and what was missing (G3).

    `missing_inputs` names the required upstream modules with no usable head;
    `missing_commands` the CP-0 command (`Run <id>`) that is absent. Both are omitted from the
    JSON while empty, so an older receipt keeps its bytes (as `Attempt.step_repairs`)."""

    module_id: Identifier
    snapshot_sha256: Hash
    reason: str
    missing_inputs: tuple[Identifier, ...] = ()
    missing_commands: tuple[Annotated[str, Field(max_length=160)], ...] = ()

    @model_serializer(mode="wrap")
    def _omit_empty_missing(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        for name in ("missing_inputs", "missing_commands"):
            if not getattr(self, name):
                data.pop(name, None)
        return data


class PublishCall(Contract):
    """One `publish` call, retained beside its `publications` record (kind `publish-calls`, no part
    of the receipt). Two refused calls at one snapshot with one reason produce one identical
    `publications` record, so only this record counts the calls the cap of two applies to."""

    sequence: int
    publication_sha256: Hash


class TransportMarker(Contract):
    """Retained by `serve_json_lines` (kind `transport`): a run served over JSON-lines is not
    resumed, as its participant and transport are held in memory only."""

    participant: str
    transport: Literal["bounded-json-lines/1"] = "bounded-json-lines/1"


class OwnerFault(Contract):
    """A `faults/` record: a failure the run cannot continue from, written before the error is
    raised. `kind` names the audit kind (or `journal`) and `digest` the record it concerns."""

    schema_version: Literal["owner-fault/1"] = "owner-fault/1"
    code: str
    kind: str | None = None
    digest: str | None = Field(default=None, max_length=160)


class TornAudit(WorkflowError):
    """The journal and the retained audit disagree in a way `open()` cannot repair. It carries the
    code `identity_mismatch` (the receipt verifier's code for evidence that does not bind) and
    `kind`/`digest` as the `OwnerFault` record names them; recovery is a rerun (G4)."""

    def __init__(self, kind: str, digest: str | None) -> None:
        super().__init__("identity_mismatch")
        self.kind, self.digest = kind, digest


class SettledHead(Contract):
    module_id: Identifier
    ticket_id: Identifier
    result_sha256: Hash
    status: Literal["accepted", "restricted", "blocked"]


class OwnerState(Contract):
    """The walk's position, read-only (G5a). Identity, counters and settled heads only: never a
    payload, a `read_inputs` body or a call body. The step fields are `None` unless a module is
    active (phase `analytical`)."""

    schema_version: Literal["owner-state/1"] = "owner-state/1"
    phase: str
    plan: tuple[Identifier, ...]
    snapshot_sha256: Hash
    # True when the journal's current sha256 differs from this instance's `_current_sha256`: the
    # binding and the counters below are then the instance's last view, not the journal's (G5a,
    # R3). A rebind that fails after `_current_sha256` is set is an owner-list item (L1).
    stale: bool
    module_id: Identifier | None
    step_id: Identifier | None
    ticket_id: Identifier | None
    attempt: int | None
    inputs_required: bool
    inputs_read: bool
    invokes_used: int
    reads_used: int
    submits_used: int
    settled: tuple[SettledHead, ...]
    refusals: tuple[RefusedBegin, ...]


class OwnerRunReceipt(Contract):
    schema_version: Literal["owner-run-receipt/1"] = "owner-run-receipt/1"
    run: Run
    pack_sha256: Hash
    snapshot_sha256: Hash
    participant: str
    transport: Literal["python-api", "bounded-json-lines/1"]
    plan: tuple[str, ...]
    heads: tuple[SettledHead, ...]
    model: ModelPublication | None
    begins: tuple[BeginRecord, ...]
    refusals: tuple[RefusedBegin, ...]
    calls: tuple[OwnerCall, ...]
    input_reads: tuple[OwnerInputRead, ...]
    submissions: tuple[OwnerSubmission, ...]
    publications: tuple[PublicationCall, ...]


def _fin(binding: OwnerBinding) -> FinancialBinding:
    """The reused CP-0/CP-1 helpers take the 11-field binding with literal module ids."""
    return FinancialBinding.model_validate(binding.model_dump())


def _owner_binding(snapshot: ExecutionSnapshot, attempt: Attempt, step_id: str) -> OwnerBinding:
    """The same 11 fields as `financial_workflow._binding`, without its CP-0/CP-1 literal."""
    return _parse(
        OwnerBinding,
        {
            "run_id": snapshot.run.run_id,
            "issuer_id": snapshot.run.issuer_id,
            "as_of": snapshot.run.as_of.isoformat(),
            "method_version": snapshot.run.method_version,
            "pack_sha256": snapshot.pack_sha256,
            "snapshot_sha256": snapshot.content_hash(),
            "module_id": attempt.module_id,
            "step_id": step_id,
            "ticket_id": attempt.ticket_id,
            "attempt": attempt.number,
            "inputs": [i.model_dump(mode="json") for i in attempt.inputs],
        },
    )


def _attempt_of(snapshot: ExecutionSnapshot, ticket_id: str) -> Attempt:
    """The snapshot's attempt of `ticket_id`; evidence naming another ticket does not bind (R4-4:
    a tamper cause, never a raw lookup failure)."""
    attempt = next((a for a in snapshot.attempts if a.ticket_id == ticket_id), None)
    if attempt is None:
        raise WorkflowError("identity_mismatch")
    return attempt


def _result_attempt(snapshot: ExecutionSnapshot, head: Head) -> Attempt:
    """The snapshot's attempt that settled `head` (R4-4, as `_attempt_of`)."""
    attempt = next((a for a in snapshot.attempts if a.result_sha256 == head.result_sha256), None)
    if attempt is None:
        raise WorkflowError("identity_mismatch")
    return attempt


def _owner_only(module_id: str) -> bool:
    """Whether the module is served by an owner core: it has no registered step chain, or one
    whose `shared_live` is false (CP-1B's chain is registered for its pinned step name only, not
    as a live contract)."""
    try:
        return not step_chain(module_id).shared_live
    except ValueError:
        return True


def _sequence(module_id: str) -> tuple[str, ...]:
    """The module's journal step sequence: its live step contract, or its owner core's
    `STEP_IDS` where it is owner-only (G1-X §2). An owner-only module without a core is a
    registration error and raises `KeyError` (`_check_specs` refuses it before any run)."""
    if not _owner_only(module_id):
        return step_chain(module_id).steps
    steps: tuple[str, ...] = tuple(_CORES[module_id].STEP_IDS)
    return steps


def _owner_historical(store: Execution, binding: OwnerBinding) -> _FrozenExecution:
    """`financial_workflow._historical` for any other module: its step sequence (the live step
    chain, else the owner core's `STEP_IDS`) is the sequence."""
    snapshot = _snapshot(store, binding.snapshot_sha256)
    attempt = _attempt_of(snapshot, binding.ticket_id)
    sequence = _sequence(attempt.module_id)
    if (
        _owner_binding(snapshot, attempt, binding.step_id) != binding
        or attempt.status != "pending"
        or attempt.issues
        or attempt.interruption
        or attempt.payload_sha256 is not None
        or attempt.result_sha256 is not None
        or current_inputs(snapshot, attempt.module_id) != attempt.inputs
        or tuple(s.step_id for s in attempt.steps) != sequence[: len(attempt.steps)]
        or any(s.status != "valid" for s in attempt.steps)
        or len(attempt.steps) >= len(sequence)
        or sequence[len(attempt.steps)] != binding.step_id
    ):
        raise WorkflowError("identity_mismatch")
    return _FrozenExecution(store, snapshot)


def _hist(store: Execution, binding: OwnerBinding) -> _FrozenExecution:
    if binding.module_id in _FINANCIAL_MODULES:
        # R4-4: the reused helper looks the ticket up unguarded; an absent one is checked first.
        _attempt_of(_snapshot(store, binding.snapshot_sha256), binding.ticket_id)
        return _historical(store, _fin(binding))
    return _owner_historical(store, binding)


def _fill(
    store: Execution, binding: OwnerBinding, payload: str
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """What the journal retains: CP-0/CP-1 as `_filled`; any other step as the entry path of
    `live.submission.submit_model_payload` (null resolution, no pre-fill), against the live
    schema of its step or, for a step outside `live.submission.STEPS`, its owner core's
    `SCHEMAS` entry (G1-X §2)."""
    if binding.module_id in _FINANCIAL_MODULES:
        return _filled(store, _fin(binding), payload)
    step_id = binding.step_id
    schema = (
        STEPS[step_id].schema if step_id in STEPS else _CORES[binding.module_id].SCHEMAS[step_id]
    )
    normal, resolved = normalise(schema, payload)
    return normal, resolved, (), ()


def _journaled_issues(
    module_id: str, step_id: str, payload: str, evidence: SourceEvidence
) -> tuple[str, ...]:
    """The tool-use rules of a `journaled` step over the session's `Seen`: `ToolRules` (absence
    and unread citations) for a live-contract step; the owner core's `RULES(text, seen)` for an
    owner-only one, where `ToolRules` raises (G1-X §2, LEAD amendment 2026-10-28)."""
    core = _CORES.get(module_id)
    if core is None:
        return ToolRules().issues(step_id, payload, seen=evidence.seen(), context=None)
    found: tuple[str, ...] = tuple(core.RULES(payload, evidence.seen()))
    return found


def _gate(
    store: Execution,
    binding: OwnerBinding,
    spec: StepSpec,
    stored: str,
    evidence: SourceEvidence,
) -> tuple[str, ...]:
    """The issues that refuse a submission before the journal, recomputed alike at submit and in
    the verifier: the module's precheck gate over the filled payload first (G1-X §4), then, only
    when the gate passes, the `precheck`-mode evidence rules. The journaled rules come later.
    The gate sees the same read-only view of the binding's snapshot at submit and in replay."""
    precheck = _PRECHECKS.get(binding.module_id)
    issues: tuple[str, ...] = ()
    if precheck is not None:
        frozen = _FrozenExecution(store, _snapshot(store, binding.snapshot_sha256))
        issues = bounded_issues(tuple(precheck(frozen, binding, stored)))
    if not issues and spec.rules == "precheck":
        issues = _evidence_issues(store, _fin(binding), stored, evidence)
    return issues


def _inputs(store: Execution, binding: OwnerBinding, spec: StepSpec) -> tuple[str, str]:
    """The (sha256, body) `read_inputs` returns for `spec`, recomputed from the journal."""
    if spec.inputs == "projection":
        return _projection(store, _fin(binding))
    if spec.inputs in ("module_context", "step_context"):
        view = _VIEWS.get(spec.step_id)
        if view is None:
            raise WorkflowError("not_permitted")
        historical = _owner_historical(store, binding)
        return view(historical, _attempt_of(historical.read(), binding.ticket_id))
    raise WorkflowError("not_permitted")


def _terminal(heads: tuple[Head, ...], run: Run, publisher: str) -> bool:
    """Publication is terminal when a producer the publisher requires holds no accepted or
    restricted head. A refusal or a blocked head further down the walk does not make it so."""
    settled = {h.module_id for h in heads if h.status in ("accepted", "restricted")}
    return not dependencies(run.requested_modules)[publisher] <= settled


def _audit(store: Execution, kind: str, digest: str) -> Path:
    return store.directory / AUDIT / kind / digest


def _retain(store: Execution, kind: str, value: Contract) -> None:
    _put(_audit(store, kind, value.content_hash()), value.model_dump_json().encode())


def _torn(store: Execution, kind: str, digest: str | None) -> TornAudit:
    """Record the fault under `faults/` and return the error to raise (the caller raises it)."""
    _retain(store, "faults", OwnerFault(code="torn_audit", kind=kind, digest=digest))
    return TornAudit(kind, digest)


def _raw(store: Execution, digest: str) -> str:
    raw = _audit(store, "payloads", digest).read_bytes()
    if _hash(raw) != digest:
        raise WorkflowError("identity_mismatch")
    return raw.decode("utf-8")


def _settled(store: Execution, module_id: str) -> SettledHead:
    snapshot = store.read()
    head = next((h for h in snapshot.heads if h.module_id == module_id), None)
    if head is None:
        raise WorkflowError("identity_mismatch")
    attempt = _result_attempt(snapshot, head)
    if attempt.status != "finished" or (head.status != "blocked" and attempt.issues):
        raise WorkflowError("identity_mismatch")
    if head.status not in ("accepted", "restricted", "blocked"):
        raise WorkflowError("identity_mismatch")
    return SettledHead(
        module_id=module_id,
        ticket_id=attempt.ticket_id,
        result_sha256=head.result_sha256,
        status=head.status,
    )


def _step(specs: Mapping[str, OwnerSpec], module_id: str, step_id: str) -> StepSpec:
    """The declared step; a recorded binding naming no declared step does not bind (R4-4)."""
    spec = specs.get(module_id)
    found = None if spec is None else next((s for s in spec.steps if s.step_id == step_id), None)
    if found is None:
        raise WorkflowError("identity_mismatch")
    return found


def _check_steps(module_id: str, spec: OwnerSpec) -> None:
    """The reference spec of one analytical module is one G1-X can serve (protocol §1-§3).

    The entry is the one `submit_review` and `_entry_outcome` dispatch for the module:
    `cp0_review` for CP-0, `model_payload` for any other live-contract module, `owner_core` for
    an owner-only one (`_owner_only`: no step chain, or one that is not `shared_live`). Every module but CP-0
    and CP-1 has an `_ENTRY_VALIDATORS` row (§2). A live-contract module keeps its registry
    chain and the chain's pack and extraction tools. An owner-only module has a registered,
    complete core: `STEP_IDS` (nonempty and distinct, as `Execution.submit_step` requires) are
    its steps (a tuple of str), `SCHEMAS[step]` is each step's schema, `submit` is callable and
    so is `RULES` when a step is journaled. Its step ids stay outside `live.submission.STEPS`
    (so `_fill` reads the core's `SCHEMAS`), it offers no statement extraction, a step has pack
    sources exactly when `host._OWNER_SCOPES` has its row, and a `journaled` step has pack
    sources (`RULES` judges the session's `Seen`). Every step: no upstream grant, some evidence
    (pack sources or a read), `module_context` or `step_context` only with a `_VIEWS` entry, and
    the financial `precheck` rules and CP-1 projection only on CP-0/CP-1, whose binding they
    take."""
    core = _CORES.get(module_id)
    chain: StepChain | None = None if _owner_only(module_id) else step_chain(module_id)
    entry = (
        "owner_core" if chain is None else "cp0_review" if module_id == "CP-0" else "model_payload"
    )
    if (
        spec.entry != entry
        or (core is None) == (chain is None)
        or (module_id not in _FINANCIAL_MODULES and module_id not in _ENTRY_VALIDATORS)
    ):
        raise WorkflowError("not_permitted")
    if chain is None:
        schemas = getattr(core, "SCHEMAS", {})
        if (
            not callable(getattr(core, "submit", None))
            or (
                any(s.rules == "journaled" for s in spec.steps)
                and not callable(getattr(core, "RULES", None))
            )
            or any(schemas.get(s.step_id) is not s.schema for s in spec.steps)
        ):
            raise WorkflowError("not_permitted")
        raw = getattr(core, "STEP_IDS", ())
        if type(raw) is not tuple or not all(type(i) is str for i in raw):
            raise WorkflowError("not_permitted")
        sequence = raw
    else:
        sequence = chain.steps
    # `Execution.submit_step` takes only a nonempty, duplicate-free sequence.
    if (
        not sequence
        or len(set(sequence)) != len(sequence)
        or tuple(s.step_id for s in spec.steps) != sequence
    ):
        raise WorkflowError("not_permitted")
    for item in spec.steps:
        if chain is None:
            served = (
                item.step_id not in STEPS
                and not item.extract
                and (item.rules != "journaled" or item.sources)
                and item.sources == ((module_id, item.step_id) in host._OWNER_SCOPES)
            )
        else:
            served = item.sources == (item.step_id in chain.pack_sources) and item.extract == (
                item.step_id in chain.extract_tools
            )
        if (
            not served
            or item.upstream_grant is not None  # grant calls are not verifiable in G1
            or (not item.sources and item.inputs == "none")
            or (item.inputs in ("module_context", "step_context") and item.step_id not in _VIEWS)
            or (
                module_id not in _FINANCIAL_MODULES
                and (item.rules == "precheck" or item.inputs == "projection")
            )
        ):
            raise WorkflowError("not_permitted")


def _check_specs(
    pack: PreparedPack,
    specs: Mapping[str, OwnerSpec],
    publication_directory: Path | None,
    directory: Path,
    *,
    published: bool = False,
) -> tuple[str, ...]:
    """Every refusal happens before anything is written. `published` (a resume that finds a
    `publications` record, P12) lets the output directory exist: it is then the run's own."""
    try:
        planned = plan(pack.run.requested_modules)
    except ValueError:
        raise WorkflowError("not_permitted") from None
    seen_deterministic = False
    for module_id, extra in specs.items():
        if module_id not in planned and (
            module_id not in OWNER_SPECS or extra != OWNER_SPECS[module_id]
        ):
            raise WorkflowError("not_permitted")
    for module_id in planned:
        spec = specs.get(module_id)
        if spec is None or spec.module_id != module_id:
            raise WorkflowError("not_permitted")
        # rules, schemas and publishers are not caller-tunable
        if spec != OWNER_SPECS.get(module_id):
            raise WorkflowError("not_permitted")
        if spec.kind == "deterministic":
            # ponytail: unreachable while OWNER_SPECS holds one deterministic module;
            # guards a future second one
            if seen_deterministic or spec.steps or spec.entry is not None or spec.publish is None:
                raise WorkflowError("not_permitted")
            seen_deterministic = True
            continue
        # A module the verifier cannot re-settle (`_PROBES[module]`) is refused here, not left to
        # a lookup failure at the end of a run.
        if module_id not in SUPPORTED_ANALYTICAL or spec.publish or module_id not in _PROBES:
            raise WorkflowError("not_permitted")
        _check_steps(module_id, spec)
    if any(OWNER_SPECS[m].kind == "deterministic" for m in planned):
        out = publication_directory
        if (
            out is None
            or (out.exists() and not published)
            or out.resolve() == directory.resolve()
            or directory.resolve() in out.resolve().parents
        ):
            raise WorkflowError("not_permitted")
    return planned


@dataclass(frozen=True)
class _Retained:
    """Every record of the audit kinds a resume reads, each parsed and checked against its digest."""

    begins: list[BeginRecord]
    refusals: list[RefusedBegin]
    calls: list[OwnerCall]
    reads: list[OwnerInputRead]
    submissions: list[OwnerSubmission]
    bindings: list[OwnerSubmissionBinding]
    publications: list[PublicationCall]
    publish_calls: list[PublishCall]


@dataclass(frozen=True)
class _Resubmit:
    """A step the journal holds pending (its payload written, its validation not finished) and the
    snapshot and attempt it was written from: the step is rebound there and its payload resubmitted."""

    before: ExecutionSnapshot
    attempt: Attempt
    step_id: str
    payload: str = ""


def _load[T: Contract](store: Execution, kind: str, model: type[T]) -> list[T]:
    """The retained records of `kind`: each parses, re-serialises to its own bytes and is named by
    its own digest, or the audit is torn."""
    directory = store.directory / AUDIT / kind
    found: list[T] = []
    for path in sorted(directory.iterdir()) if directory.is_dir() else ():
        if path.name.startswith("."):  # Finder's .DS_Store and the like: never a record
            continue
        if not path.is_file() or len(path.name) != 64:
            raise _torn(store, kind, path.name[:160])
        raw = path.read_bytes()
        try:
            value = model.model_validate_json(raw)
        except ValueError:
            raise _torn(store, kind, path.name) from None
        if value.model_dump_json().encode() != raw or value.content_hash() != path.name:
            raise _torn(store, kind, path.name)
        found.append(value)
    return found


def _retained_audit(store: Execution) -> _Retained:
    return _Retained(
        begins=_load(store, "begins", BeginRecord),
        refusals=_load(store, "refused-begin", RefusedBegin),
        calls=_load(store, "calls", OwnerCall),
        reads=_load(store, "input-reads", OwnerInputRead),
        submissions=_load(store, "submissions", OwnerSubmission),
        bindings=_load(store, "bindings", OwnerSubmissionBinding),
        publications=_load(store, "publications", PublicationCall),
        publish_calls=_load(store, "publish-calls", PublishCall),
    )


def _chain_of(store: Execution) -> list[ExecutionSnapshot]:
    """The journal's snapshots from the created one to the current one, along `parent`."""
    try:
        chain = [store.read()]
        while chain[-1].parent is not None:
            chain.append(_snapshot(store, chain[-1].parent))
    except (OSError, ValueError):
        raise _torn(store, "snapshots", None) from None
    chain.reverse()
    return chain


def _covered(store: Execution, got: _Retained, position: Mapping[str, int]) -> int:
    """The chain position the retained transitions reach, walking them in order (F4).

    A begin, a submission and a publication each record `before -> after`; sorted, each must start
    where the previous one ended, from the created snapshot (a refused submission or publication
    changes no snapshot and has width 0). A record that names a snapshot outside the chain, or a
    gap between two records, is torn. Calls, reads, refusals and unread submits are only placed:
    they must name a snapshot of the chain."""
    spans: list[tuple[int, int, str]] = []
    transitions: list[tuple[str, Contract, str, str]] = [
        ("begins", b, b.snapshot_before_sha256, b.snapshot_after_sha256) for b in got.begins
    ]
    transitions += [
        ("submissions", s, s.binding.binding.snapshot_sha256, s.snapshot_after_sha256)
        for s in got.submissions
    ]
    transitions += [
        ("publications", p, p.snapshot_before_sha256, p.snapshot_after_sha256)
        for p in got.publications
    ]
    for kind, record, first, last in transitions:
        if first not in position or last not in position or position[last] < position[first]:
            raise _torn(store, kind, record.content_hash())
        spans.append((position[first], position[last], record.content_hash()))
    placed: list[tuple[str, Contract, str]] = [
        ("calls", c, c.binding.snapshot_sha256) for c in got.calls
    ]
    placed += [("input-reads", r, r.binding.snapshot_sha256) for r in got.reads]
    placed += [("refused-begin", r, r.snapshot_sha256) for r in got.refusals]
    for kind, record, digest in placed:
        if digest not in position:
            raise _torn(store, kind, record.content_hash())
    cursor = 0
    for start, end, digest in sorted(spans):
        if start != cursor:
            raise _torn(store, "journal", digest)
        cursor = end
    return cursor


def _begin_between(
    before: ExecutionSnapshot, after: ExecutionSnapshot, analytical: frozenset[str]
) -> BeginRecord | None:
    """The `BeginRecord` of the one transition `before -> after` when it is exactly a begin of an
    analytical module (a pure function of the two snapshots, `_expected_begin`), else None."""
    if after.heads != before.heads or len(after.attempts) != len(before.attempts) + 1:
        return None
    new = after.attempts[-1]
    if after.attempts[:-1] != before.attempts or new.module_id not in analytical:
        return None
    try:
        expected = _expected_begin(before, new.module_id, new.ticket_id)
    except WorkflowError:
        return None
    if new != expected:
        return None
    return BeginRecord(
        module_id=new.module_id,
        ticket_id=new.ticket_id,
        attempt=new.number,
        snapshot_before_sha256=before.content_hash(),
        snapshot_after_sha256=after.content_hash(),
    )


def _pending_between(before: ExecutionSnapshot, after: ExecutionSnapshot) -> _Resubmit | None:
    """`after` is `before` plus one pending step on one pending attempt and nothing else: what
    `Execution.submit_step` writes before it validates (execution.py)."""
    if after.heads != before.heads or len(after.attempts) != len(before.attempts):
        return None
    changed = [(a, b) for a, b in zip(after.attempts, before.attempts, strict=True) if a != b]
    if len(changed) != 1:
        return None
    new, old = changed[0]
    if (
        new.ticket_id != old.ticket_id
        or new.status != "pending"
        or len(new.steps) != len(old.steps) + 1
        or new.steps[-1].status != "pending"
        or new.model_copy(update={"steps": old.steps}) != old
    ):
        return None
    return _Resubmit(before=before, attempt=old, step_id=new.steps[-1].step_id)


def _tail(
    store: Execution,
    chain: Sequence[ExecutionSnapshot],
    cursor: int,
    got: _Retained,
    analytical: frozenset[str],
    deterministic: str | None,
) -> BeginRecord | _Resubmit | None:
    """What the journal holds past the last retained transition (F4).

    Nothing: the audit is whole. One begin with no `BeginRecord` (window (b), between
    `store.begin` and the begins retain): rebuilt, retained and returned. One pending step with
    its binding retained and no `submissions` record (window (a), during validation): returned for
    the step to be rebound and its payload resubmitted. A publisher attempt with no `publications`
    record (window (c), between `publish` and its retain), a stray binding, or any other gap is
    torn: a second `publish` would double-publish and the call record cannot be rebuilt."""
    recorded = {p.ticket_id for p in got.publications}
    if deterministic is not None and any(
        a.module_id == deterministic and a.ticket_id not in recorded for a in chain[-1].attempts
    ):
        raise _torn(store, "publications", chain[-1].content_hash())
    known = {s.binding.content_hash() for s in got.submissions}
    stray = [b for b in got.bindings if b.content_hash() not in known]
    tail = chain[cursor + 1 :]
    if not tail:
        if stray:
            raise _torn(store, "bindings", stray[0].content_hash())
        return None
    before = chain[cursor]
    if len(tail) == 1 and not stray:
        record = _begin_between(before, tail[0], analytical)
        if record is not None:
            _retain(store, "begins", record)
            return record
    pending = _pending_between(before, tail[0]) if len(tail) == 1 else None
    if pending is None or not stray:
        raise _torn(store, "journal", tail[0].content_hash())
    binding = stray[0]
    if (
        len(stray) != 1
        or binding.binding.snapshot_sha256 != before.content_hash()
        or (binding.binding.ticket_id, binding.binding.step_id)
        != (pending.attempt.ticket_id, pending.step_id)
    ):
        raise _torn(store, "bindings", binding.content_hash())
    new = next(a for a in tail[0].attempts if a.ticket_id == pending.attempt.ticket_id)
    try:
        payload = _raw(store, binding.payload_sha256)
        stored = _fill(store, binding.binding, payload)[0]
    except (OSError, ValueError):
        raise _torn(store, "payloads", binding.payload_sha256) from None
    if _hash(stored.encode()) != new.steps[-1].payload_sha256:
        raise _torn(store, "bindings", binding.content_hash())
    return replace(pending, payload=payload)


class OwnerWorkflow:
    def __init__(
        self,
        store: Execution,
        planned: tuple[str, ...],
        publication_directory: Path | None,
    ) -> None:
        self._setup(store, planned, publication_directory)
        self._begin(self._analytical[0])

    def _setup(
        self,
        store: Execution,
        planned: tuple[str, ...],
        publication_directory: Path | None,
    ) -> None:
        # Bind to the reference specs, never to the caller's mapping (checked at create).
        self._specs: Mapping[str, OwnerSpec] = MappingProxyType(
            {m: OWNER_SPECS[m] for m in planned}
        )
        self._store, self._plan = store, planned
        self._publication_directory = publication_directory
        self._operation = Lock()
        self._calls: list[OwnerCall] = []
        self._reads: list[OwnerInputRead] = []
        self._submissions: list[OwnerSubmission] = []
        self._publications: list[PublicationCall] = []
        self._begins: list[BeginRecord] = []
        self._refusals: list[RefusedBegin] = []
        self._refusal_kind: Literal["not_authorized", "blocked"] | None = None
        self._model: ModelPublication | None = None
        self._participant = "trusted-python"
        self._transport: Literal["python-api", "bounded-json-lines/1"] = "python-api"
        self._limits: Counter[tuple[str, str, str]] = Counter()
        self._analytical = tuple(m for m in planned if self._specs[m].kind == "analytical")
        self._phase = "analytical"  # analytical | walked | complete | failed
        # The publisher the walk is stopped at, until its publication settles (G1a).
        self._resume_after: str | None = None
        self._publisher_done = False
        self._publish_calls = 0  # `publish` calls so far; the cap of two applies to this
        self._sealed = False
        self._epoch_calls: list[OwnerCall] = []
        self._session: SourceSession | None = None
        self._spec: StepSpec
        self._binding: OwnerBinding
        self._current_sha256 = ""
        # Replayed call id -> retained call id, for a session `open()` rebuilt (see `open`).
        self._alias: dict[str, str] = {}

    @classmethod
    def create(
        cls,
        directory: Path,
        pack: PreparedPack,
        *,
        specs: Mapping[str, OwnerSpec] = OWNER_SPECS,
        publication_directory: Path | None = None,
    ) -> "OwnerWorkflow":
        planned = _check_specs(pack, specs, publication_directory, directory)
        if not any(OWNER_SPECS[m].kind == "analytical" for m in planned):
            raise WorkflowError("not_permitted")
        return cls(Execution.create(directory, pack), planned, publication_directory)

    @classmethod
    def open(
        cls,
        directory: Path,
        *,
        specs: Mapping[str, OwnerSpec] = OWNER_SPECS,
        publication_directory: Path | None = None,
    ) -> "OwnerWorkflow":
        """Resume a killed run from its journal and retained audit (G5b).

        Refused (`not_permitted`) unless `directory/current` exists, and as `create` refuses
        (`_check_specs`; an existing output directory is allowed once a publication is recorded).
        `__init__` is bypassed: it would begin CP-0. The lists the receipt is built from are
        rebuilt from `owner-run-audit/`, ordered by position in the journal's snapshot chain, and
        the walk continues from the journal (`_advance`), which recomputes what no record shows:
        a refusal retained or not, the CP-MODEL stop, the next begin.

        The journal and the audit are reconciled by walking the chain (F4): every retained
        transition (begin, submission, publication) starts where the previous one ended. What the
        journal holds beyond the last one is either nothing, or one of two repairable windows, or
        `TornAudit` (`identity_mismatch` plus a `faults/` record naming kind and digest):
        (a) during validation, one pending step with its payload and binding retained and no
        `submissions` record: the step is rebound at the snapshot before the pending write and the
        caller resubmits the same payload, which continues validation; (b) between `store.begin`
        and the begins retain: the `BeginRecord` is rebuilt from the two snapshots and retained;
        (c) between `publish` and the publications retain, a stray binding, a step already
        validated but unrecorded, and any other gap are torn; (c) is detected before the
        output-exists refusal, so an output a real `publish` left behind does not hide it.
        Window (a) is completed here (R5): the retained payload is resubmitted through
        `submit_review` before `open()` returns, so no caller holds the pending binding; a
        validator that raises again raises out of `open()` and a later `open()` finds window (a).
        The calls of each closed binding are taken from the submission that lists them; a call
        listed by none and outside the open epoch is torn, the closed calls are replayed and each
        submission's journal step is checked (a forged record is refused here, not first at
        `write_receipt`). A submit before `read_inputs` writes nothing and is not charged.

        Single writer: exactly one instance may write a run directory at a time. `open()` takes
        no lock and the audit has no lock file; two live instances over one directory are not
        detected (`run_pathway` resume holds the run directory's `flock` for the whole run, 3b).

        Calls: a kill with unsubmitted `invoke` calls is resumed in the same epoch. A rebuilt
        `SourceSession` starts at sequence 0 with new call ids, so the retained epoch is replayed
        through its public `invoke` (the verifier's own method, deterministic); each replay must
        equal the retained call but for its id, and the retained ids are kept by remapping them in
        `submit_review` (`_alias`). A call killed before its retain is lost, so `invokes_used`
        can be one less than before the kill.

        Known limits: a call killed between its increment and its retain is not counted; a submit
        that raised after `_limits` was incremented is not counted; a run served over JSON-lines
        (`transport` marker) is refused `not_permitted`; `phase` `failed` is rebuilt from the
        last publication being `failed` with a publisher head, a pending publisher attempt or the
        output directory still present; a run whose `receipt.sha256` exists is sealed (the
        receipt file is written before the seal)."""
        if not (directory / "current").is_file():
            raise WorkflowError("not_permitted")
        store = Execution(directory)
        recorded = directory / AUDIT / "publications"
        publishers = {m for m, spec in OWNER_SPECS.items() if spec.kind == "deterministic"}
        # R8: the output directory may exist once a publication is recorded, and also when the
        # journal holds a publisher attempt with no record (window (c)): `_tail` then raises
        # `TornAudit` instead of the output-exists refusal hiding it.
        planned = _check_specs(
            store.pack(),
            specs,
            publication_directory,
            directory,
            published=(recorded.is_dir() and any(recorded.iterdir()))
            or any(a.module_id in publishers for a in store.read().attempts),
        )
        marker = directory / AUDIT / "transport"
        if marker.is_dir() and any(marker.iterdir()):
            raise WorkflowError("not_permitted")  # served over JSON-lines: not resumed
        if not any(OWNER_SPECS[m].kind == "analytical" for m in planned):
            raise WorkflowError("not_permitted")
        workflow = cls.__new__(cls)
        workflow._setup(store, planned, publication_directory)
        workflow._resume()
        return workflow

    def _resume(self) -> None:
        store = self._store
        got = _retained_audit(store)
        chain = _chain_of(store)
        position = {s.content_hash(): i for i, s in enumerate(chain)}
        cursor = _covered(store, got, position)
        deterministic = next(
            (m for m in self._plan if self._specs[m].kind == "deterministic"), None
        )
        tail = _tail(store, chain, cursor, got, frozenset(self._analytical), deterministic)
        if isinstance(tail, BeginRecord):
            got.begins.append(tail)
        self._rebuild_lists(got, position)
        snapshot = chain[-1]
        self._current_sha256 = snapshot.content_hash()
        pending = [a for a in snapshot.attempts if a.status == "pending"]
        if len(pending) > 1:
            raise _torn(store, "journal", snapshot.content_hash())
        if deterministic is not None:
            self._rebuild_publication(snapshot, deterministic)
        if (store.directory / AUDIT / "receipt.sha256").exists():
            self._sealed, self._phase = True, "complete"
        elif pending:
            self._resume_pending(pending[0], tail if isinstance(tail, _Resubmit) else None, got)
        else:
            self._continue_walk(snapshot, deterministic)
        self._check_closed()

    def _rebuild_lists(self, got: _Retained, position: Mapping[str, int]) -> None:
        """The receipt's lists, their order and the counters, from the retained records."""
        store = self._store
        for kind, items in (("begins", got.begins), ("refused-begin", got.refusals)):
            for item in items:
                if item.module_id not in self._analytical:
                    raise _torn(store, kind, item.content_hash())
        seen: set[str] = set()
        for refusal in got.refusals:  # a module is refused at most once; the second is the fault
            if refusal.module_id in seen:
                raise _torn(store, "refused-begin", refusal.content_hash())
            seen.add(refusal.module_id)
        self._begins = sorted(got.begins, key=lambda b: position[b.snapshot_before_sha256])
        self._refusals = sorted(got.refusals, key=lambda r: self._plan.index(r.module_id))
        self._submissions = sorted(got.submissions, key=lambda s: s.sequence)
        for expected, submission in enumerate(self._submissions, 1):
            if submission.sequence != expected:
                raise _torn(store, "submissions", submission.content_hash())
        self._calls = sorted(
            got.calls, key=lambda c: (position[c.binding.snapshot_sha256], c.sequence)
        )
        self._reads = sorted(
            got.reads, key=lambda r: (position[r.binding.snapshot_sha256], r.sequence)
        )
        self._rebuild_publications(got, position)
        self._check_listed()
        if self._refusals:  # the first refusal names the submit outcome (L2)
            self._refusal_kind = (
                "not_authorized" if self._refusals[0].missing_commands else "blocked"
            )
        limits: Counter[tuple[str, str, str]] = Counter()
        for call in self._calls:
            limits[(call.binding.ticket_id, call.binding.step_id, "invoke")] += 1
        for read in self._reads:
            limits[(read.binding.ticket_id, read.binding.step_id, "read_inputs")] += 1
        for submission in self._submissions:
            bound = submission.binding.binding
            limits[(bound.ticket_id, bound.step_id, "submit_review")] += 1
        self._limits = limits

    def _rebuild_publications(self, got: _Retained, position: Mapping[str, int]) -> None:
        """The receipt's publications in call order and the count the cap of two applies to.

        Each `publish` call retains a `publish-calls` record naming its `publications` record
        (written first), because two refused calls at one snapshot with one reason leave one
        record. A record no call names (a run from before the call records) follows in journal
        order; a call whose record never reached the audit still counts."""
        store = self._store
        by_hash = {p.content_hash(): p for p in got.publications}
        calls = sorted(got.publish_calls, key=lambda c: c.sequence)
        for expected, call in enumerate(calls, 1):
            if call.sequence != expected:
                raise _torn(store, "publish-calls", call.content_hash())
        named = {c.publication_sha256 for c in calls}
        rest = sorted(
            (p for digest, p in by_hash.items() if digest not in named),
            key=lambda p: (position[p.snapshot_before_sha256], position[p.snapshot_after_sha256]),
        )
        self._publications = [
            by_hash[c.publication_sha256] for c in calls if c.publication_sha256 in by_hash
        ] + rest
        self._publish_calls = max(len(calls), len(self._publications))

    def _check_listed(self) -> None:
        """Each submission's `call_ids` are exactly the first calls of its binding (R6), and the
        reads of a step are numbered from 1 without a gap (a submission does not list reads)."""
        by_id = {c.call_id: c for c in self._calls}
        for submission in self._submissions:
            for n, call_id in enumerate(submission.binding.call_ids, 1):
                call = by_id.get(call_id)
                if call is None or call.binding != submission.binding.binding or call.sequence != n:
                    raise _torn(self._store, "submissions", submission.content_hash())
        taken: Counter[tuple[str, str]] = Counter()
        for read in self._reads:
            key = (read.binding.ticket_id, read.binding.step_id)
            taken[key] += 1
            if read.sequence != taken[key]:
                raise _torn(self._store, "input-reads", read.content_hash())

    def _check_closed(self) -> None:
        """What `open()` can check without a model: a call neither listed by a submission nor in
        the open epoch is torn; the calls of every closed binding replay to the retained
        receipts; each submission's journal step and issues are the ones it records. The verifier
        repeats these (and more) at `write_receipt`; here they stop a forged record from being
        adopted into the rebuilt lists."""
        store = self._store
        listed = {i for s in self._submissions for i in s.binding.call_ids}
        epoch = {c.call_id for c in self._epoch_calls}
        for call in self._calls:
            if call.call_id not in listed and call.call_id not in epoch:
                raise _torn(store, "calls", call.content_hash())
        active = self._binding if self._phase == "analytical" else None
        groups: dict[str, list[OwnerCall]] = {}
        for call in self._calls:
            groups.setdefault(call.binding.content_hash(), []).append(call)
        for group in groups.values():
            if group[0].binding != active:
                self._replay_closed(group)
        for submission in self._submissions:
            self._check_submission(submission)

    def _replay_closed(self, group: list[OwnerCall]) -> None:
        """Replay one closed binding's calls on a session pinned to its snapshot, as the verifier
        does, and require each to equal the retained call but for its id."""
        binding = group[0].binding
        try:
            spec = _step(self._specs, binding.module_id, binding.step_id)
            if spec.sources:
                session = SourceSession.from_execution(
                    _hist(self._store, binding), binding.ticket_id, binding.step_id
                )
                replayed = [_parse(OwnerCall, session.invoke(c.tool, c.arguments)) for c in group]
            else:  # no source tool is offered: every call was refused
                replayed = [c.model_copy(update={"status": "refused"}) for c in group]
        except (OSError, ValueError):
            raise _torn(self._store, "calls", group[0].content_hash()) from None
        for call, again in zip(group, replayed, strict=True):
            if again.model_copy(update={"call_id": call.call_id}) != call or (
                not spec.sources and (call.error_code != "not_permitted" or call.body is not None)
            ):
                raise _torn(self._store, "calls", call.content_hash())

    def _check_submission(self, submission: OwnerSubmission) -> None:
        """The journal step a submission names is the one it records (its payload, output and
        issues), and a refused one is what the gate refuses again."""
        store, bound = self._store, submission.binding
        try:
            historical = _hist(store, bound.binding)
            spec = _step(self._specs, bound.binding.module_id, bound.binding.step_id)
            stored = _raw(store, submission.stored_payload_sha256)
            issues = _gate(historical, bound.binding, spec, stored, bound.source_evidence)
            after = _attempt_of(
                _snapshot(store, submission.snapshot_after_sha256), bound.binding.ticket_id
            )
            before = _attempt_of(historical.read(), bound.binding.ticket_id)
        except (OSError, ValueError):
            raise _torn(store, "submissions", submission.content_hash()) from None
        if submission.disposition == "refused":
            sound = issues == submission.issues and bool(issues)
        else:
            candidates = (
                after.steps
                if len(after.steps) > len(before.steps)
                else after.step_repairs[len(before.step_repairs) :]
            )
            steps = [s for s in candidates[-1:] if s.content_hash() == submission.step_sha256]
            sound = (
                not issues
                and len(steps) == 1
                and steps[0].payload_sha256 == submission.stored_payload_sha256
                and steps[0].output_sha256 == submission.step_output_sha256
                and (steps[0].status == "valid") == (submission.disposition == "valid")
                and (submission.disposition == "valid" or steps[0].issues == submission.issues)
                and (submission.disposition != "valid" or not submission.issues)
            )
        if not sound:
            raise _torn(store, "submissions", submission.content_hash())

    def _rebuild_publication(self, snapshot: ExecutionSnapshot, publisher: str) -> None:
        """`_model` and `_publisher_done`, as `publish` leaves them: the walk resumes after a
        published module or a terminal refusal (the stop snapshot has no usable producer)."""
        published = [p for p in self._publications if p.status == "published"]
        if published:
            if not {publisher, "CP-1"} <= {h.module_id for h in snapshot.heads}:
                raise _torn(self._store, "publications", published[-1].content_hash())
            model = _record(self._store, publisher)
            self._model = ModelPublication(
                ticket_id=model.ticket_id,
                result_sha256=model.result_sha256,
                cp1_result_sha256=_record(self._store, "CP-1").result_sha256,
                files=published[-1].files,
            )
            self._publisher_done = True
        elif self._publications and self._publications[-1].status == "refused":
            stop = _snapshot(self._store, self._publications[-1].snapshot_before_sha256)
            self._publisher_done = _terminal(stop.heads, stop.run, publisher)

    def _failed_publication(self, snapshot: ExecutionSnapshot, publisher: str) -> bool:
        """`publish` left the phase `failed`: its last record is `failed` and a publisher head, a
        pending publisher attempt or the output directory remains (its cleanup did not finish)."""
        if not self._publications or self._publications[-1].status != "failed":
            return False
        return (
            any(h.module_id == publisher for h in snapshot.heads)
            or any(a.module_id == publisher and a.status == "pending" for a in snapshot.attempts)
            or (self._publication_directory is not None and self._publication_directory.exists())
        )

    def _resume_pending(self, attempt: Attempt, resubmit: _Resubmit | None, got: _Retained) -> None:
        """Re-activate the journal's one pending attempt at its next step, as `submit_review` does
        after a valid or an invalid step; its epoch is restored from the retained calls."""
        if attempt.module_id not in self._analytical:
            # A publisher attempt whose interruption failed: `publish` left the phase failed.
            if attempt.ticket_id in {p.ticket_id for p in self._publications}:
                self._phase = "failed"
                self._resume_after = attempt.module_id
                return
            raise _torn(self._store, "publications", attempt.ticket_id)
        done = sum(s.status == "valid" for s in attempt.steps)
        steps = _sequence(attempt.module_id)
        if done >= len(steps):
            raise _torn(self._store, "journal", attempt.ticket_id)
        if resubmit is None:
            self._activate(attempt, steps[done])
        else:
            self._activate(resubmit.attempt, resubmit.step_id, at=resubmit.before)
        self._restore_epoch()
        if resubmit is not None:
            # Window (a), R5: finish the validation the kill interrupted, with the payload the
            # audit retained, so that no caller ever holds the pending binding. A validator that
            # raises again raises out of `open()`; the next `open()` finds window (a) as before.
            self.submit_review(resubmit.payload)

    def _restore_epoch(self) -> None:
        """The active binding's retained calls are the open epoch, in sequence order. A source
        session is rebuilt by replaying them (see `open`)."""
        epoch = sorted(
            (c for c in self._calls if c.binding == self._binding), key=lambda c: c.sequence
        )
        for expected, call in enumerate(epoch, 1):
            if call.sequence != expected:  # a gap: the first call after it is the fault
                raise _torn(self._store, "calls", call.content_hash())
        if self._session is not None:
            for call in epoch:
                replayed = _parse(OwnerCall, self._session.invoke(call.tool, call.arguments))
                if replayed.model_copy(update={"call_id": call.call_id}) != call:
                    raise _torn(self._store, "calls", call.content_hash())
                self._alias[replayed.call_id] = call.call_id
        self._epoch_calls = epoch

    def _continue_walk(self, snapshot: ExecutionSnapshot, publisher: str | None) -> None:
        """No attempt is pending: continue from the last module the walk reached (begun or
        refused), or from the publisher's stop. A refusal never retained is recomputed here."""
        reached = [self._plan.index(b.module_id) for b in self._begins]
        reached += [self._plan.index(r.module_id) for r in self._refusals]
        if publisher is not None and self._publications:
            reached.append(self._plan.index(publisher))
        if not reached:  # killed between `Execution.create` and the first begin
            self._begin(self._analytical[0])
            return
        last = self._plan[max(reached)]
        if last == publisher:
            if self._publisher_done:  # `publish` settled: the walk resumes after the stop
                self._phase = "analytical"
                self._advance(last)
            else:
                failed = publisher is not None and self._failed_publication(snapshot, publisher)
                self._phase = "failed" if failed else "walked"
                self._resume_after = last
            return
        attempts = [a for a in snapshot.attempts if a.module_id == last]
        if attempts and attempts[-1].number == 0 and attempts[-1].issues:
            self._begin(last)  # attempt 0 settled invalid: its one repair is begun next
        else:
            self._advance(last)

    @property
    def binding(self) -> OwnerBinding:
        """The active step's binding (module, step, ticket, attempt); read-only (O5 Q1)."""
        return self._binding

    @property
    def spec(self) -> StepSpec:
        """The active step's spec; read-only (O5 Q1)."""
        return self._spec

    @property
    def phase(self) -> str:
        """The walk's phase (analytical, walked, complete or failed); read-only (O5 Q6)."""
        return self._phase

    def state(self) -> OwnerState:
        """The walk's position as a fresh immutable value (G5a). It takes `_operation` without
        blocking, like the other methods, but not `_locked()`: a sealed run is inspectable, and a
        stale instance (which `open()` relies on) still answers because it never calls
        `_current()`; the snapshot is read from the journal."""
        if not self._operation.acquire(blocking=False):
            raise WorkflowError("not_permitted")
        try:
            snapshot = self._store.read()
            stale = snapshot.content_hash() != self._current_sha256
            settled = tuple(_settled(self._store, h.module_id) for h in snapshot.heads)
            if self._phase != "analytical":  # no module is active: the last binding is history
                return OwnerState(
                    phase=self._phase,
                    plan=self._plan,
                    snapshot_sha256=snapshot.content_hash(),
                    stale=stale,
                    module_id=None,
                    step_id=None,
                    ticket_id=None,
                    attempt=None,
                    inputs_required=False,
                    inputs_read=False,
                    invokes_used=0,
                    reads_used=0,
                    submits_used=0,
                    settled=settled,
                    refusals=tuple(self._refusals),
                )
            binding = self._binding

            def used(name: str) -> int:
                return self._limits[(binding.ticket_id, binding.step_id, name)]

            return OwnerState(
                phase=self._phase,
                plan=self._plan,
                snapshot_sha256=snapshot.content_hash(),
                stale=stale,
                module_id=binding.module_id,
                step_id=binding.step_id,
                ticket_id=binding.ticket_id,
                attempt=binding.attempt,
                inputs_required=self._spec.inputs != "none",
                inputs_read=any(r.binding == binding for r in self._reads),
                invokes_used=used("invoke"),
                reads_used=used("read_inputs"),
                submits_used=used("submit_review"),
                settled=settled,
                refusals=tuple(self._refusals),
            )
        finally:
            self._operation.release()

    @property
    def _refused(self) -> bool:
        """Publication is terminal (H1): CP-MODEL's required producer has no settled head."""
        snapshot = self._store.read()
        publisher = next((m for m in self._plan if self._specs[m].kind == "deterministic"), None)
        return publisher is not None and _terminal(snapshot.heads, snapshot.run, publisher)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        if not self._operation.acquire(blocking=False):
            raise WorkflowError("not_permitted")
        try:
            if self._sealed:
                raise WorkflowError("not_permitted")
            yield
        finally:
            self._operation.release()

    def _current(self) -> ExecutionSnapshot:
        snapshot = self._store.read()
        if snapshot.content_hash() != self._current_sha256:
            raise WorkflowError("stale_binding")
        self._store.pack(snapshot)
        return snapshot

    def _activate(
        self, attempt: Attempt, step_id: str, *, at: ExecutionSnapshot | None = None
    ) -> None:
        """Bind the step at the journal's current snapshot, or (`open()` resuming a step whose
        payload the journal already holds pending) at the earlier snapshot `at`: its binding, its
        source session and its history are then those of `at`, the journal being ahead of them."""
        snapshot = self._store.read()
        bound = snapshot if at is None else at
        self._spec = _step(self._specs, attempt.module_id, step_id)
        self._binding = _owner_binding(bound, attempt, step_id)
        self._current_sha256 = snapshot.content_hash()
        self._session = (
            SourceSession.from_execution(
                self._store if at is None else _FrozenExecution(self._store, at),
                attempt.ticket_id,
                step_id,
            )
            if self._spec.sources
            else None
        )
        self._epoch_calls = []
        self._alias = {}
        _hist(self._store, self._binding)

    def _begin(self, module_id: str) -> bool:
        """Begin one analytical module. A refusal is retained with what it lacked, and the walk
        continues through `_advance` (G3), so the CP-MODEL stop and the end of the plan still
        apply."""
        before = self._store.read()
        kind: Literal["not_authorized", "blocked"]
        try:
            attempt = self._store.begin(module_id)
        except NotAuthorized as error:
            reason, kind = str(error), "not_authorized"
            missing = _missing_inputs(before, module_id, error)
        except ValueError as error:
            # Only the blocked-edge refusal is a retained refusal: after a blocked producer, or
            # when every missing input is itself a refused module of this walk. Any other
            # ValueError is a defect and propagates.
            missing = _missing_inputs(before, module_id, error)
            refused = {r.module_id for r in self._refusals}
            if not str(error).startswith(BLOCKED_EDGE) or not _retainable(
                before, missing[0], refused
            ):
                raise
            reason, kind = str(error), "blocked"
        else:
            after = self._store.read()
            record = BeginRecord(
                module_id=module_id,
                ticket_id=attempt.ticket_id,
                attempt=attempt.number,
                snapshot_before_sha256=before.content_hash(),
                snapshot_after_sha256=after.content_hash(),
            )
            _retain(self._store, "begins", record)
            self._begins.append(record)
            self._activate(attempt, self._specs[module_id].steps[0].step_id)
            return True
        refusal = RefusedBegin(
            module_id=module_id,
            snapshot_sha256=before.content_hash(),
            reason=reason,
            missing_inputs=missing[0],
            missing_commands=missing[1],
        )
        _retain(self._store, "refused-begin", refusal)
        self._refusals.append(refusal)
        if self._refusal_kind is None:  # the first refusal names the submit outcome (L2)
            self._refusal_kind = kind
        self._current_sha256 = before.content_hash()
        self._advance(module_id)
        return False

    def _advance(self, module_id: str) -> None:
        """Move past a settled, blocked or published module to the next planned one: an
        analytical module is begun, the deterministic publisher is a stop (`publish` resumes the
        walk after it), and none left ends the walk."""
        later = self._plan[self._plan.index(module_id) + 1 :]
        if not later:
            self._finish_walk()
        elif self._specs[later[0]].kind == "deterministic":
            self._phase = "walked"
            self._resume_after = later[0]
        else:
            self._begin(later[0])

    def _finish_walk(self) -> None:
        self._phase = "walked"
        if self._publisher_done or all(self._specs[m].kind == "analytical" for m in self._plan):
            self._phase = "complete"

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            self._current()
            if self._phase != "analytical":  # no module is active: there is no binding to read
                raise WorkflowError("not_permitted")
            key = (self._binding.ticket_id, self._binding.step_id, "invoke")
            if self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            if self._session is None:
                call = OwnerCall(
                    schema_version="tool-receipt/1",
                    call_id=str(uuid4()),
                    sequence=len(self._epoch_calls) + 1,
                    binding=self._binding,
                    tool=tool_name,
                    arguments=arguments,
                    status="refused",
                    body=None,
                    error_code="not_permitted",
                    source_evidence=SourceEvidence(),
                )
            else:
                call = _parse(OwnerCall, self._session.invoke(tool_name, arguments))
            call = _parse(OwnerCall, call.model_dump(mode="json"))
            if call.binding != self._binding or call.sequence != len(self._epoch_calls) + 1:
                raise WorkflowError("identity_mismatch")
            _retain(self._store, "calls", call)
            self._epoch_calls.append(call)
            self._calls.append(call)
            return call.model_dump(mode="json")

    def read_inputs(self) -> dict[str, Any]:
        with self._locked():
            self._current()
            if self._phase != "analytical":
                raise WorkflowError("not_permitted")
            key = (self._binding.ticket_id, self._binding.step_id, "read_inputs")
            if self._spec.inputs == "none" or self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            digest, body = _inputs(self._store, self._binding, self._spec)
            self._limits[key] += 1
            record = OwnerInputRead(
                binding=self._binding, sequence=self._limits[key], inputs_sha256=digest, body=body
            )
            _retain(self._store, "input-reads", record)
            self._reads.append(record)
            self._current()
            return record.model_dump(mode="json")

    def submit_review(self, payload: str) -> dict[str, Any]:
        with self._locked():
            self._current()
            if (
                self._phase != "analytical"
                or type(payload) is not str
                or len(payload.encode()) > MAX_LINE
            ):
                raise WorkflowError("not_permitted")
            key = (self._binding.ticket_id, self._binding.step_id, "submit_review")
            if self._limits[key] >= MAX_CALLS:
                raise WorkflowError("not_permitted")
            spec = self._spec
            # G1-X §3: a step whose inputs are not "none" (every session-less step, and a step
            # with pack sources that also has a view) is read on its own binding first. A
            # precondition refusal (R1a): not charged to the submit cap, nothing written (the
            # CP-1D lease), so a resume has nothing to rebuild.
            if spec.inputs != "none" and not any(r.binding == self._binding for r in self._reads):
                raise WorkflowError("not_permitted")
            self._limits[key] += 1
            evidence = (
                self._epoch_calls[-1].source_evidence if self._epoch_calls else SourceEvidence()
            )
            payload_bytes = payload.encode()
            binding = OwnerSubmissionBinding(
                binding=self._binding,
                payload_sha256=_hash(payload_bytes),
                call_ids=tuple(c.call_id for c in self._epoch_calls),
                successful_call_ids=tuple(c.call_id for c in self._epoch_calls if c.status == "ok"),
                source_evidence=evidence,
            )
            if (
                self._session is not None
                and self._unaliased(
                    _parse(OwnerSubmissionBinding, self._session.bind_submission(payload))
                )
                != binding
            ):
                raise WorkflowError("identity_mismatch")
            _put(_audit(self._store, "payloads", binding.payload_sha256), payload_bytes)
            _retain(self._store, "bindings", binding)
            stored, resolved, paths, kinds = _fill(self._store, self._binding, payload)
            stored_hash = _hash(stored.encode())
            _put(_audit(self._store, "payloads", stored_hash), stored.encode())
            module_id = self._binding.module_id
            # G1-X §4: issues here refuse the submission: no journal step, no attempt consumed.
            issues = _gate(self._store, self._binding, spec, stored, evidence)
            rules = (
                (lambda text: _journaled_issues(module_id, spec.step_id, text, evidence))
                if spec.rules == "journaled"
                else None
            )
            self._current()
            attempt = None
            disposition: Literal["valid", "invalid", "refused"] = "refused"
            submitted_step = None
            if not issues:
                entry = self._specs[module_id].entry
                ticket_id = self._binding.ticket_id
                if entry == "cp0_review":
                    attempt = submit_cp0_review(self._store, ticket_id, stored)
                else:
                    # G1-X §2: an owner core journals its step and returns the same `Submitted`
                    # as `submit_model_payload`, so the identity check below holds for both.
                    submitted: Submitted = (
                        _CORES[module_id].submit(
                            self._store, ticket_id, spec.step_id, payload, rules
                        )
                        if entry == "owner_core"
                        else submit_model_payload(
                            self._store, ticket_id, spec.step_id, payload, rules=rules
                        )
                    )
                    if (
                        submitted.payload,
                        submitted.nulls_resolved,
                        submitted.prefilled,
                        submitted.prefilled_kinds,
                    ) != (stored, resolved, paths, kinds):
                        raise WorkflowError("identity_mismatch")
                    attempt = submitted.journal
                candidates = (
                    attempt.steps
                    if attempt.steps and attempt.steps[-1].step_id == spec.step_id
                    else attempt.step_repairs
                )
                if (
                    not candidates
                    or candidates[-1].payload_sha256 != stored_hash
                    or candidates[-1].step_id != spec.step_id
                ):
                    raise WorkflowError("identity_mismatch")
                submitted_step = candidates[-1]
                disposition = (
                    "valid"
                    if submitted_step.status == "valid" and not attempt.issues
                    else "invalid"
                )
                issues = submitted_step.issues or attempt.issues
            after = self._store.read()
            try:
                canonical = spec.schema.model_validate_json(stored).content_hash()
            except ValueError:
                canonical = None
            after_hash = after.content_hash()
            record = OwnerSubmission(
                sequence=len(self._submissions) + 1,
                binding=binding,
                stored_payload_sha256=stored_hash,
                canonical_review_sha256=canonical,
                disposition=disposition,
                issues=issues,
                snapshot_after_sha256=after_hash,
                nulls_resolved=resolved,
                prefilled=paths,
                prefilled_kinds=kinds,
                step_sha256=None if submitted_step is None else submitted_step.content_hash(),
                step_output_sha256=None if submitted_step is None else submitted_step.output_sha256,
            )
            _retain(self._store, "submissions", record)
            self._submissions.append(record)
            self._current_sha256 = after_hash
            if attempt is not None:
                chain = _sequence(module_id)
                if disposition == "valid" and attempt.status == "finished":
                    if len(attempt.steps) != len(chain):
                        raise WorkflowError("identity_mismatch")
                    self._advance(module_id)
                elif disposition == "valid":
                    self._activate(attempt, chain[len(attempt.steps)])
                elif attempt.status == "pending":
                    self._activate(attempt, spec.step_id)
                elif attempt.number == 0:
                    self._begin(module_id)
                else:
                    self._advance(module_id)  # attempt 1 settled blocked
            return {
                "schema_version": "financial-review-outcome/1",
                "status": disposition,
                "issues": list(issues),
                "step_id": spec.step_id,
                "refusal": self._refusal_code(),
                "snapshot_sha256": self._current_sha256,
                "next_step": self._binding.step_id if self._phase == "analytical" else None,
                "stored_payload_sha256": stored_hash,
                "prefilled": list(paths),
            }

    def _unaliased(self, bound: OwnerSubmissionBinding) -> OwnerSubmissionBinding:
        """The session's binding with the call ids of a replayed epoch renamed to the retained
        ones (`open()`); the identity when the session is the one that made the calls."""
        if not self._alias:
            return bound
        return bound.model_copy(
            update={
                "call_ids": tuple(self._alias.get(i, i) for i in bound.call_ids),
                "successful_call_ids": tuple(
                    self._alias.get(i, i) for i in bound.successful_call_ids
                ),
            }
        )

    def _refusal_code(self) -> str | None:
        if not self._refusals:
            return None
        module = self._refusals[0].module_id.lower().replace("-", "")
        return f"{module}_{self._refusal_kind}"

    def publish(self) -> dict[str, Any]:
        with self._locked():
            before = self._current()
            publisher = next(
                (self._specs[m] for m in self._plan if self._specs[m].kind == "deterministic"),
                None,
            )
            if (
                self._phase != "walked"
                or self._publish_calls >= 2
                or publisher is None
                or publisher.publish is None
                or self._publication_directory is None
            ):
                raise WorkflowError("not_permitted")
            output = self._publication_directory
            ticket = None
            reason = None
            files: dict[str, str] = {}
            status: Literal["published", "refused", "failed"] = "refused"
            terminal = False
            try:
                attempt = publisher.publish(self._store, output=output)
                ticket = attempt.ticket_id
                if verify_cp_model_publication(self._store, output):
                    raise WorkflowError("identity_mismatch")
                model = _record(self._store, publisher.module_id)
                files = _files(output)
                self._model = ModelPublication(
                    ticket_id=model.ticket_id,
                    result_sha256=model.result_sha256,
                    cp1_result_sha256=_record(self._store, "CP-1").result_sha256,
                    files=files,
                )
                status = "published"
            except Exception as error:
                # Documented fail-closed: record why, finalize every owned partial publication.
                reason = str(error)
                known = {a.ticket_id for a in before.attempts}
                new = [a for a in self._store.read().attempts if a.ticket_id not in known]
                if new:
                    status = "failed"
                    ticket = new[0].ticket_id if len(new) == 1 else None
                    if len(new) != 1 or new[0].module_id != publisher.module_id:
                        self._phase = "failed"
                        raise WorkflowError("identity_mismatch") from error
                    if new[0].status == "pending":
                        try:
                            self._store.interrupt(
                                new[0].ticket_id, "Publication did not complete: " + reason
                            )
                        except Exception as cleanup_error:  # noqa: BLE001 - quarantine stays independent
                            reason += "; interruption failed: " + type(cleanup_error).__name__
                            self._phase = "failed"
                    if output.exists():
                        for name in FILES:
                            try:
                                path = output / name
                                if path.is_file():
                                    files[name] = _hash(path.read_bytes())
                            except OSError as hash_error:
                                reason += "; partial hash failed: " + type(hash_error).__name__
                        try:
                            output.rename(output.with_name(output.name + ".failed-" + str(uuid4())))
                        except OSError as quarantine_error:
                            reason += "; quarantine failed: " + type(quarantine_error).__name__
                            self._phase = "failed"
                    if any(h.module_id == publisher.module_id for h in self._store.read().heads):
                        self._phase = "failed"
                elif self._refused and isinstance(error, CpModelRefused):
                    terminal = True
            after = self._store.read()
            record = PublicationCall(
                snapshot_before_sha256=before.content_hash(),
                snapshot_after_sha256=after.content_hash(),
                status=status,
                reason=reason,
                ticket_id=ticket,
                files=files,
            )
            _retain(
                self._store,
                "publish-calls",
                PublishCall(
                    sequence=self._publish_calls + 1, publication_sha256=record.content_hash()
                ),
            )
            _retain(self._store, "publications", record)
            self._publications.append(record)
            self._publish_calls += 1
            self._current_sha256 = after.content_hash()
            outcome = {
                "status": "ok" if status == "published" else "refused",
                "error_code": None
                if status == "published"
                else self._refusal_code() or "publication_refused",
                "snapshot_sha256": self._current_sha256,
            }
            if (status == "published" or terminal) and self._phase != "failed":
                # The publication settled: the walk resumes after the stop, or ends here. The
                # result above is the publication's own, taken before the resume.
                self._publisher_done = True
                resume, self._resume_after = self._resume_after, None
                self._phase = "analytical"
                if resume is None:
                    self._finish_walk()
                else:
                    self._advance(resume)
            return {
                **outcome,
                "next_step": self._binding.step_id if self._phase == "analytical" else None,
            }

    def write_receipt(self, destination: Path) -> OwnerRunReceipt:
        with self._locked():
            snapshot = self._current()
            if self._phase != "complete":
                raise WorkflowError("not_permitted")
            receipt = OwnerRunReceipt(
                run=snapshot.run,
                pack_sha256=snapshot.pack_sha256,
                snapshot_sha256=snapshot.content_hash(),
                participant=self._participant,
                transport=self._transport,
                plan=self._plan,
                heads=tuple(_settled(self._store, h.module_id) for h in snapshot.heads),
                model=self._model,
                begins=tuple(self._begins),
                refusals=tuple(self._refusals),
                calls=tuple(self._calls),
                input_reads=tuple(self._reads),
                submissions=tuple(self._submissions),
                publications=tuple(self._publications),
            )
            _verify(
                self._store,
                receipt,
                publication_directory=self._publication_directory if self._model else None,
                sealed=False,
            )
            self._current()
            # The receipt file first, the seal last: a kill between them leaves a run `open()` does
            # not treat as sealed, so `write_receipt` can rebuild it (equal bytes are accepted).
            _put(destination, receipt.model_dump_json().encode())
            _put(self._store.directory / AUDIT / "receipt.sha256", receipt.content_hash().encode())
            self._current()
            self._sealed = True
            return receipt


def _verify_audit(store: Execution, receipt: OwnerRunReceipt) -> None:
    collections: dict[str, tuple[Contract, ...]] = {
        "calls": receipt.calls,
        "input-reads": receipt.input_reads,
        "submissions": receipt.submissions,
        "bindings": tuple(s.binding for s in receipt.submissions),
        "publications": receipt.publications,
        "begins": receipt.begins,
        "refused-begin": receipt.refusals,
    }
    for kind, values in collections.items():
        expected = {v.content_hash(): v.model_dump_json().encode() for v in values}
        directory = store.directory / AUDIT / kind
        actual = (
            {p.name for p in directory.iterdir() if not p.name.startswith(".")}
            if directory.exists()
            else set()
        )
        if actual != set(expected) or any(
            _audit(store, kind, digest).read_bytes() != raw for digest, raw in expected.items()
        ):
            raise WorkflowError("identity_mismatch")
    if len({c.call_id for c in receipt.calls}) != len(receipt.calls):
        raise WorkflowError("identity_mismatch")
    for records in (receipt.calls, receipt.input_reads):
        counts = Counter((r.binding.ticket_id, r.binding.step_id) for r in records)
        if any(count > MAX_CALLS for count in counts.values()):
            raise WorkflowError("identity_mismatch")
    sub_counts = Counter(
        (s.binding.binding.ticket_id, s.binding.binding.step_id) for s in receipt.submissions
    )
    if any(count > MAX_CALLS for count in sub_counts.values()):
        raise WorkflowError("identity_mismatch")


def _missing_inputs(
    snapshot: ExecutionSnapshot, module_id: str, error: ValueError
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """What a refused begin lacked: `(missing_inputs, missing_commands)` (G3).

    A `NotAuthorized` lacks CP-0's `Run <module_id>` command and nothing else. The blocked-edge
    `ValueError` lacks the required upstream modules with no usable head, in plan order: no head,
    or a blocked head under an edge that does not restrict (`execution.current_inputs`' own
    rule). Any other error names nothing."""
    if isinstance(error, NotAuthorized):
        return (), (f"Run {module_id}",)
    if not str(error).startswith(BLOCKED_EDGE):
        return (), ()
    order = plan(snapshot.run.requested_modules)
    required = dependencies(snapshot.run.requested_modules).get(module_id, set())
    heads = {h.module_id: h for h in snapshot.heads}

    def usable(item: str) -> bool:
        head = heads.get(item)
        if head is None:
            return False
        if head.status in ("accepted", "restricted"):
            return True
        return head.status == "blocked" and edge_rule(module_id, item) == "restricted"

    missing = [item for item in required if not usable(item)]
    missing.sort(key=lambda item: (order.index(item) if item in order else len(order), item))
    return tuple(missing), ()


def _verify_refusal(before: ExecutionSnapshot, refusal: RefusedBegin, refused: set[str]) -> None:
    """The refusal is the journal's own answer at `before`: `current_inputs` raises with the same
    reason, and `_missing_inputs` of that error equals what was recorded. A blocked-edge refusal
    needs a blocked head in `before` or every missing input itself refused in the walk."""
    try:
        current_inputs(before, refusal.module_id)
    except ValueError as error:
        if str(error) != refusal.reason:
            raise WorkflowError("identity_mismatch") from None
        inputs, commands = _missing_inputs(before, refusal.module_id, error)
        if (inputs, commands) != (refusal.missing_inputs, refusal.missing_commands):
            raise WorkflowError("identity_mismatch") from None
        if not isinstance(error, NotAuthorized) and (
            not str(error).startswith(BLOCKED_EDGE) or not _retainable(before, inputs, refused)
        ):
            raise WorkflowError("identity_mismatch") from None
    else:
        raise WorkflowError("identity_mismatch")


def _retainable(before: ExecutionSnapshot, missing: tuple[str, ...], refused: set[str]) -> bool:
    """A blocked-edge `ValueError` is a retained refusal only after a blocked producer, or when
    every missing input is a module refused in this walk; anything else is a defect (G7)."""
    if any(h.status == "blocked" for h in before.heads):
        return True
    return bool(missing) and all(item in refused for item in missing)


def _expected_begin(before: ExecutionSnapshot, module_id: str, ticket_id: str) -> Attempt:
    """What `Execution.begin(module_id)` yields on `before` (execution.py `begin`), with the
    ticket id taken from the record because a uuid cannot be replayed: no pending attempt; the
    inputs `current_inputs` binds; `previous` = attempts of the same module and inputs, and a
    begin is refused when `previous` holds two or its last one is not rejected. A begin that
    succeeded cannot have raised, so each refusal here is a forged record (R4-4)."""
    if any(a.status == "pending" for a in before.attempts):
        raise WorkflowError("identity_mismatch")
    try:
        inputs = current_inputs(before, module_id)
    except NotAuthorized:
        raise WorkflowError("identity_mismatch") from None
    except ValueError:
        raise WorkflowError("identity_mismatch") from None
    previous = [a for a in before.attempts if a.module_id == module_id and a.inputs == inputs]
    if previous and (len(previous) >= 2 or not previous[-1].issues):
        raise WorkflowError("identity_mismatch")
    return Attempt(
        ticket_id=ticket_id,
        module_id=module_id,
        inputs=inputs,
        number=len(previous),
        repair_of=previous[-1].ticket_id if previous else None,
        repair_issues=previous[-1].issues if previous else (),
    )


def _verify_begins(store: Execution, receipt: OwnerRunReceipt, analytical: frozenset[str]) -> None:
    """Each analytical attempt has exactly one retained begin, and that begin is what
    `Execution.begin` yields on its `before`: the attempt list grows by exactly `_expected_begin`
    and nothing else changes in it."""
    snapshot = store.read()
    attempts = Counter(a.ticket_id for a in snapshot.attempts if a.module_id in analytical)
    if Counter(b.ticket_id for b in receipt.begins) != attempts:
        raise WorkflowError("identity_mismatch")
    for begin in receipt.begins:
        before = _snapshot(store, begin.snapshot_before_sha256)
        after = _snapshot(store, begin.snapshot_after_sha256)
        expected = _expected_begin(before, begin.module_id, begin.ticket_id)
        if begin.attempt != expected.number or after.attempts != (*before.attempts, expected):
            raise WorkflowError("identity_mismatch")


def _verify_transition(
    before: ExecutionSnapshot,
    after: ExecutionSnapshot,
    kind: str,
    ticket_id: str | None,
    deterministic: str | None,
) -> None:
    """One recorded transition changes only what its operation may: a begin changes no head (its
    one added attempt is `_verify_begins`'); a submission changes only its ticket's attempt and
    that module's head; a publication only the deterministic module's head (its attempt is
    `_verify_publications`')."""
    if kind == "begin":
        if after.heads != before.heads:
            raise WorkflowError("identity_mismatch")
        return
    if kind == "publication":
        module_id = deterministic
    else:
        attempt = next((a for a in before.attempts if a.ticket_id == ticket_id), None)
        if (
            attempt is None
            or [a.ticket_id for a in after.attempts] != [a.ticket_id for a in before.attempts]
            or any(
                a != b
                for a, b in zip(after.attempts, before.attempts, strict=True)
                if a.ticket_id != ticket_id
            )
        ):
            raise WorkflowError("identity_mismatch")
        module_id = attempt.module_id
        # The attempt keeps the identity it was begun with: a step may not relabel a repair as a
        # first try (or the reverse). `Execution.begin` fixes these fields; nothing later changes
        # them.
        begun = next(a for a in after.attempts if a.ticket_id == ticket_id)
        if any(
            getattr(begun, field) != getattr(attempt, field)
            for field in ("module_id", "inputs", "number", "repair_of", "repair_issues")
        ):
            raise WorkflowError("identity_mismatch")
    if (
        tuple(h for h in after.heads if h.module_id != module_id)
        != tuple(h for h in before.heads if h.module_id != module_id)
        or sum(h.module_id == module_id for h in after.heads) > 1
    ):
        raise WorkflowError("identity_mismatch")


def _verify_chain(
    receipt: OwnerRunReceipt,
    chain: Sequence[ExecutionSnapshot],
    deterministic: str | None,
    planned: tuple[str, ...],
) -> None:
    """R6-1: the recorded coordinates are one gapless chain from the created snapshot to the
    final one. Every begin, submission and publication is a transition `before -> after`;
    ordered along the ancestry, each starts where the previous one ended, the first at the root
    and the last at the final snapshot (a refusal sits at the last `after` of the modules
    planned before the publisher or at the final snapshot, by `_verify_walk`). The transitions
    keep the walk's order: modules planned before the publisher, its publications, then modules
    planned after it. Each transition passes `_verify_transition`. Within a ticket, the first submission is bound to its begin's
    `after` and each later one to the previous submission's `after`; every call and read is
    bound to one of those binding snapshots."""
    position = {snapshot.content_hash(): index for index, snapshot in enumerate(chain)}
    transitions: list[tuple[int, int, str, str | None]] = [
        (
            position[b.snapshot_before_sha256],
            position[b.snapshot_after_sha256],
            "begin",
            b.ticket_id,
        )
        for b in receipt.begins
    ]
    transitions += [
        (
            position[s.binding.binding.snapshot_sha256],
            position[s.snapshot_after_sha256],
            "submission",
            s.binding.binding.ticket_id,
        )
        for s in receipt.submissions
    ]
    transitions += [
        (
            position[p.snapshot_before_sha256],
            position[p.snapshot_after_sha256],
            "publication",
            p.ticket_id,
        )
        for p in receipt.publications
    ]
    # The receipt lists begins and publications in chain order: `_verify_walk` reads "the next
    # begin" and "the first publication" from these lists, so a reordering would move a refusal.
    for listed in (receipt.begins, receipt.publications):
        places = [position[item.snapshot_before_sha256] for item in listed]
        if places != sorted(places):
            raise WorkflowError("identity_mismatch")
    transitions.sort(key=lambda item: item[:2])
    # The walk order is bound (F2): modules planned before the publisher, then its publications,
    # then modules planned after it; a later module begun before the stop breaks the sequence.
    module_of = {b.ticket_id: b.module_id for b in receipt.begins}
    stop = planned.index(deterministic) if deterministic is not None else len(planned)
    stage = 0
    cursor = 0
    last_begun = -1  # begins follow plan order; a refused module is skipped (G3)
    for before, after, kind, ticket_id in transitions:
        if before != cursor or after < before:
            raise WorkflowError("identity_mismatch")
        if kind == "publication":
            phase = 1
        else:
            module_id = module_of.get(ticket_id or "")
            if module_id not in planned:
                raise WorkflowError("identity_mismatch")
            phase = 0 if planned.index(module_id) < stop else 2
            if kind == "begin":
                if planned.index(module_id) < last_begun:
                    raise WorkflowError("identity_mismatch")
                last_begun = planned.index(module_id)
        if phase < stage:
            raise WorkflowError("identity_mismatch")
        stage = phase
        cursor = after
        _verify_transition(chain[before], chain[after], kind, ticket_id, deterministic)
    if cursor != len(chain) - 1:
        raise WorkflowError("identity_mismatch")
    expected = {b.ticket_id: b.snapshot_after_sha256 for b in receipt.begins}
    bindings: dict[str, set[str]] = {t: {digest} for t, digest in expected.items()}
    for submission in receipt.submissions:
        binding = submission.binding.binding
        if expected.get(binding.ticket_id) != binding.snapshot_sha256:
            raise WorkflowError("identity_mismatch")
        expected[binding.ticket_id] = submission.snapshot_after_sha256
        bindings[binding.ticket_id].add(binding.snapshot_sha256)
    bound = [c.binding for c in receipt.calls] + [r.binding for r in receipt.input_reads]
    for binding in bound:
        if binding.snapshot_sha256 not in bindings.get(binding.ticket_id, ()):
            raise WorkflowError("identity_mismatch")


def _verify_walk(
    store: Execution,
    receipt: OwnerRunReceipt,
    analytical: tuple[str, ...],
    planned: tuple[str, ...],
    deterministic: str | None,
) -> None:
    """Each planned analytical module is settled or refused, never both and never neither (G3).

    A refusal does not end the walk: the next module is begun. A refusal sits on the snapshot the
    next begin started from; with no later begin before the stop, on the first publication's
    `before` when the module is planned before CP-MODEL and a publication follows, else on the
    final snapshot (a refusal does not change the journal, so consecutive refusals share one)."""
    snapshot = store.read()
    heads = {h.module_id for h in snapshot.heads}
    refused_ids = [r.module_id for r in receipt.refusals]
    refused = set(refused_ids)
    if len(refused) != len(refused_ids) or len(heads) != len(snapshot.heads):
        raise WorkflowError("identity_mismatch")
    if not refused <= set(analytical):
        raise WorkflowError("identity_mismatch")
    for module_id in analytical:
        # settled xor refused; a refused module has no attempt (it was never begun)
        if (module_id in heads) == (module_id in refused):
            raise WorkflowError("identity_mismatch")
        if module_id in refused and any(a.module_id == module_id for a in snapshot.attempts):
            raise WorkflowError("identity_mismatch")
    blocked = [
        m
        for m in analytical
        if any(h.module_id == m and h.status == "blocked" for h in snapshot.heads)
    ]
    if blocked and not receipt.refusals and analytical[-1] not in blocked:
        later = analytical[analytical.index(blocked[0]) + 1 :]
        if later and later[0] not in heads:
            raise WorkflowError("identity_mismatch")
    before_stop = planned.index(deterministic) if deterministic is not None else len(planned)
    final = snapshot.content_hash()

    def refused_on(module_id: str) -> str:
        index = planned.index(module_id)
        pre_stop = index < before_stop
        for begin in receipt.begins:  # chronological: the first later one is the next begin
            position = planned.index(begin.module_id)
            if position > index and (not pre_stop or position < before_stop):
                return begin.snapshot_before_sha256
        if receipt.publications and pre_stop:
            return receipt.publications[0].snapshot_before_sha256
        return final

    for refusal in receipt.refusals:
        if refusal.module_id not in planned or refusal.snapshot_sha256 != refused_on(
            refusal.module_id
        ):
            raise WorkflowError("identity_mismatch")
        _verify_refusal(_snapshot(store, refusal.snapshot_sha256), refusal, refused)


def _interrupted_issues(interruption: str) -> tuple[str, ...]:
    """The issues `execution.settle` writes for an interruption (its own rule, replayed).

    An interruption the producer could not have stored is a forgery: a blank reason, which
    `Execution.interrupt` refuses (execution.py:890), or one over the bound, since the stored
    value is already shortened."""
    reason = shortened(interruption, MAX_INTERRUPTION_CHARS)
    if not interruption.strip() or reason != interruption:
        raise WorkflowError("identity_mismatch")
    return bounded_issues(tuple(dict.fromkeys((f"Interrupted: {reason}",))))


def _verify_publications(
    store: Execution, receipt: OwnerRunReceipt, terminal_refusal: bool, deterministic: str | None
) -> None:
    """Every begun publisher attempt and non-begin refusal has its retained transition."""
    snapshot = store.read()
    attempts = {a.ticket_id: a for a in snapshot.attempts if a.module_id == deterministic}
    recorded = Counter(p.ticket_id for p in receipt.publications if p.ticket_id is not None)
    if deterministic is None:
        if receipt.publications or receipt.model is not None:
            raise WorkflowError("identity_mismatch")
        return
    if recorded != Counter(attempts.keys()) or not 1 <= len(receipt.publications) <= 2:
        raise WorkflowError("identity_mismatch")
    previous_after = None
    for index, publication in enumerate(receipt.publications):
        before = _snapshot(store, publication.snapshot_before_sha256)
        after = _snapshot(store, publication.snapshot_after_sha256)
        if previous_after is not None and previous_after != publication.snapshot_before_sha256:
            raise WorkflowError("identity_mismatch")
        previous_after = publication.snapshot_after_sha256
        if publication.status == "refused":
            if (
                before != after
                or publication.ticket_id is not None
                or publication.files
                or not publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            if not terminal_refusal and not (
                publication.reason.startswith("Output ")
                and "already exists; publish into a new directory" in publication.reason
            ):
                raise WorkflowError("identity_mismatch")
            continue
        known = {a.ticket_id for a in before.attempts}
        added = [a for a in after.attempts if a.ticket_id not in known]
        if (
            len(added) != 1
            or added[0].module_id != deterministic
            or added[0].ticket_id != publication.ticket_id
            or added[0] != attempts.get(publication.ticket_id)
            or tuple(a for a in after.attempts if a.ticket_id != publication.ticket_id)
            != before.attempts
            or set(publication.files) - set(FILES)
        ):
            raise WorkflowError("identity_mismatch")
        attempt = added[0]
        # The publisher's `begin` obeys the producer's rule at its own `before`; the finished
        # attempt is compared on the identity fields `begin` sets (the rest is the publication's).
        expected = _expected_begin(before, deterministic, attempt.ticket_id)
        if (attempt.module_id, attempt.inputs, attempt.number) != (
            expected.module_id,
            expected.inputs,
            expected.number,
        ) or (attempt.repair_of, attempt.repair_issues) != (
            expected.repair_of,
            expected.repair_issues,
        ):
            raise WorkflowError("identity_mismatch")
        if publication.status == "published":
            if (
                index != len(receipt.publications) - 1
                or attempt.status != "finished"
                or attempt.issues
                or publication.reason is not None
                or receipt.model is None
                or publication.files != receipt.model.files
            ):
                raise WorkflowError("identity_mismatch")
        elif (
            attempt.status != "finished"
            or attempt.interruption is None
            or not publication.reason
            or attempt.issues != _interrupted_issues(attempt.interruption)
        ):
            raise WorkflowError("identity_mismatch")


def _verify_calls_reads(
    store: Execution, receipt: OwnerRunReceipt, specs: Mapping[str, OwnerSpec]
) -> None:
    replayed: dict[str, SourceSession] = {}
    # R6: a sealed run has no open epoch, so every call is one a submission at its binding lists.
    listed = {
        (s.binding.binding, call_id) for s in receipt.submissions for call_id in s.binding.call_ids
    }
    if any((call.binding, call.call_id) not in listed for call in receipt.calls):
        raise WorkflowError("identity_mismatch")
    for call in receipt.calls:
        historical = _hist(store, call.binding)
        key = call.binding.content_hash()
        prior = [
            c for c in receipt.calls if c.binding == call.binding and c.sequence < call.sequence
        ]
        if call.sequence != len(prior) + 1 or call.sequence > MAX_CALLS:
            raise WorkflowError("identity_mismatch")
        if _step(specs, call.binding.module_id, call.binding.step_id).sources:
            if key not in replayed:
                replayed[key] = SourceSession.from_execution(
                    historical, call.binding.ticket_id, call.binding.step_id
                )
            expected = _parse(OwnerCall, replayed[key].invoke(call.tool, call.arguments))
            if expected.model_copy(update={"call_id": call.call_id}) != call:
                raise WorkflowError("identity_mismatch")
        elif (
            call.status != "refused"
            or call.error_code != "not_permitted"
            or call.body is not None
            or call.source_evidence != SourceEvidence()
        ):
            raise WorkflowError("identity_mismatch")
    for read in receipt.input_reads:
        read_spec = _step(specs, read.binding.module_id, read.binding.step_id)
        if read_spec.inputs == "none":
            raise WorkflowError("identity_mismatch")
        digest, body = _inputs(store, read.binding, read_spec)
        earlier = [
            r
            for r in receipt.input_reads
            if (r.binding.ticket_id, r.binding.step_id)
            == (read.binding.ticket_id, read.binding.step_id)
            and r.sequence < read.sequence
        ]
        if (
            (read.inputs_sha256, read.body) != (digest, body)
            or read.sequence != len(earlier) + 1
            or read.sequence > MAX_CALLS
        ):
            raise WorkflowError("identity_mismatch")


def _entry_outcome(
    historical: _FrozenExecution, binding: OwnerBinding, payload: str, attempt: Attempt
) -> StepValidation:
    """What the module's own entry validator says of `attempt` (its last step the one under
    replay) on the historical snapshot: `cp0_workflow._validate_review` for CP-0; for CP-1 the
    stage validator the pre-fill selects (`_validate_prefilled` when a marked field stays
    unset or unbound) or the promotion's `_quality_stage`; for any other module the validator
    registered in `_ENTRY_VALIDATORS` (the one its entry, or its owner core's `submit`, hands
    `Execution.submit_step`). A module without one is refused, never passed."""
    pack = historical.pack()
    module_id, step_id = binding.module_id, binding.step_id
    if module_id == "CP-0":
        return cp0_validate_review(historical, pack, attempt)
    if module_id == "CP-1":
        if step_id == "quality":
            return _quality_stage(historical, pack, attempt)[0]
        normal, _ = normalise(STEPS[step_id].schema, payload)
        known = known_bindings(historical, binding.ticket_id, step_id)
        filled = prefill(STEPS[step_id].schema, normal, known, PREFILLED[step_id])
        if filled.unbound or filled.unset:
            return _validate_prefilled(historical, known, step_id, pack, attempt)
        return validate_cp1_stage(historical, pack, attempt)
    validate = _ENTRY_VALIDATORS.get(module_id)
    if validate is None:
        raise WorkflowError("not_permitted")
    return validate(historical, pack, attempt)


def _unbounded_step_issues(
    spec: StepSpec, validator_issues: tuple[str, ...], journaled: tuple[str, ...]
) -> tuple[str, ...]:
    """The issues the core hands `settle` for an invalid step, before the journal's bound (rule
    issues arrive capped, 0d-c) (R4-1, R4-2): the entry validator's, with the journaled rule
    issues appended and de-duplicated exactly as `live.submission._with_rules` composes them (no
    dedupe when no rule found anything)."""
    if spec.rules == "journaled" and journaled:
        return tuple(dict.fromkeys((*validator_issues, *journaled)))
    return tuple(validator_issues)


def _verify_invalid_step(
    store: Execution,
    historical: _FrozenExecution,
    spec: StepSpec,
    binding: OwnerBinding,
    raw_payload: str,
    after: Attempt,
    step: StepSubmission,
    journaled: tuple[str, ...],
) -> Module | None:
    """Replay one invalid step as `Execution.submit_step` retained it (R4-1, R4-2, R5-3).

    The step's inputs are the attempt's plus one `step:` input per step completed before it;
    its output is the entry validator's replayed at the historical snapshot (hash and bytes) and
    its issues that validator's, bounded. A first rejection of a within-attempt-repair step
    leaves the attempt pending with the step in `step_repairs` (returns None); any other invalid
    step settles the attempt: the empty candidate, the `settle` of that candidate under the same
    issues, the finished attempt and the stored result must all be exactly what the core
    produces, and the rebuilt result is returned for the head check (R5-1)."""
    before = _attempt_of(historical.read(), binding.ticket_id)
    pending = step.model_copy(update={"status": "pending", "output_sha256": None, "issues": ()})
    view = before.model_copy(update={"steps": (*before.steps, pending)})
    outcome = _entry_outcome(historical, binding, raw_payload, view)
    unbounded = _unbounded_step_issues(spec, outcome.issues, journaled)
    inputs = (
        *before.inputs,
        *(Input(input_id="step:" + s.step_id, sha256=s.content_hash()) for s in before.steps),
    )
    if (
        step.status != "invalid"
        or not unbounded
        or step.issues != bounded_issues(unbounded)
        or step.inputs != inputs
        or not outcome.retained_as(step)
        or (
            outcome.output is not None
            and store.step_output(step.output_sha256 or "") != outcome.output
        )
    ):
        raise WorkflowError("identity_mismatch")
    repairable = binding.step_id in WITHIN_ATTEMPT_REPAIR.get(binding.module_id, frozenset())
    if repairable and all(item.step_id != binding.step_id for item in before.step_repairs):
        if after != before.model_copy(update={"step_repairs": (*before.step_repairs, step)}):
            raise WorkflowError("identity_mismatch")
        return None
    snapshot = historical.read()
    run = snapshot.run
    empty = Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=binding.module_id,
        inputs=before.inputs,
        attempt=before.number,
    ).model_dump_json()
    submitted = before.model_copy(
        update={"steps": (*before.steps, step), "payload_sha256": text_sha256(empty)}
    )
    finished, result = settle(
        snapshot.model_copy(
            update={
                "parent": snapshot.content_hash(),
                "attempts": tuple(
                    view if a.ticket_id == binding.ticket_id else a for a in snapshot.attempts
                ),
            }
        ),
        submitted,
        empty,
        lambda _: unbounded,
        pack=historical.pack(),
        load=store.head_module,
    )
    if (
        finished != after
        or after.result_sha256 is None
        or store.payload(after.payload_sha256 or "") != empty
        or store.result(after.result_sha256) != result
    ):
        raise WorkflowError("identity_mismatch")
    return result


def _verify_attempts(
    snapshot: ExecutionSnapshot, receipt: OwnerRunReceipt, analytical: frozenset[str]
) -> None:
    """The repair chain of every analytical attempt (R4-1): attempt 0 repairs nothing; attempt 1
    repairs the finished, rejected attempt 0 of the same module and inputs, carrying its issues;
    a finished attempt with issues stopped on a recorded invalid step."""
    recorded = {(s.binding.binding.ticket_id, s.step_sha256) for s in receipt.submissions}
    seen: dict[str, Attempt] = {}
    repaired: set[str] = set()
    for attempt in (a for a in snapshot.attempts if a.module_id in analytical):
        if attempt.ticket_id in seen:
            raise WorkflowError("identity_mismatch")
        if attempt.number == 0:
            if attempt.repair_of is not None or attempt.repair_issues:
                raise WorkflowError("identity_mismatch")
        else:
            previous = seen.get(attempt.repair_of or "")
            if (
                previous is None
                or previous.ticket_id in repaired
                or previous.module_id != attempt.module_id
                or previous.number != 0
                or previous.status != "finished"
                or not previous.issues
                or previous.inputs != attempt.inputs
                or attempt.repair_issues != previous.issues
            ):
                raise WorkflowError("identity_mismatch")
            repaired.add(previous.ticket_id)
        if attempt.status == "finished" and attempt.issues:
            last = attempt.steps[-1] if attempt.steps else None
            if (
                last is None
                or last.status != "invalid"
                or attempt.interruption is not None
                or (attempt.ticket_id, last.content_hash()) not in recorded
            ):
                raise WorkflowError("identity_mismatch")
        seen[attempt.ticket_id] = attempt


@dataclass(frozen=True)
class _Settlement:
    """A finished attempt as the submission that settled it left it (R5-1): the attempt in that
    submission's `snapshot_after`, and the result its rebuilt invalid-step settlement produced
    (None when a valid step settled it; the module's probe re-settles that one)."""

    attempt: Attempt
    result: Module | None


def _verify_submissions(
    store: Execution, receipt: OwnerRunReceipt, specs: Mapping[str, OwnerSpec]
) -> tuple[list[tuple[str, str, str]], dict[str, _Settlement]]:
    """Replay every submission at its historical snapshot. Returns the valid steps and, per
    ticket, the settlement of each attempt a submission finished (at most one per ticket)."""
    valid: list[tuple[str, str, str]] = []
    settlements: dict[str, _Settlement] = {}
    for sequence, submission in enumerate(receipt.submissions, 1):
        if submission.sequence != sequence:
            raise WorkflowError("identity_mismatch")
        binding = submission.binding
        spec = _step(specs, binding.binding.module_id, binding.binding.step_id)
        # R4-3, G1-X §3: as at runtime, a step whose inputs are not "none" is read on its own
        # binding before its payload is filled or its gate runs.
        if spec.inputs != "none" and not any(
            r.binding == binding.binding for r in receipt.input_reads
        ):
            raise WorkflowError("identity_mismatch")
        historical = _hist(store, binding.binding)
        raw = _raw(store, binding.payload_sha256)
        filled, resolved, paths, kinds = _fill(historical, binding.binding, raw)
        if (filled, resolved, paths, kinds) != (
            _raw(store, submission.stored_payload_sha256),
            submission.nulls_resolved,
            submission.prefilled,
            submission.prefilled_kinds,
        ):
            raise WorkflowError("identity_mismatch")
        scoped = [c for c in receipt.calls if c.binding == binding.binding]
        prefix = scoped[: len(binding.call_ids)]
        evidence = prefix[-1].source_evidence if prefix else SourceEvidence()
        if (
            binding.call_ids != tuple(c.call_id for c in prefix)
            or binding.successful_call_ids != tuple(c.call_id for c in prefix if c.status == "ok")
            or binding.source_evidence != evidence
        ):
            raise WorkflowError("identity_mismatch")
        # G1-X §4: the gate is recomputed for every submission. A refused record must reproduce
        # exactly its issues; a journaled (valid or invalid) step must yield none.
        issues = _gate(historical, binding.binding, spec, filled, evidence)
        after = _snapshot(store, submission.snapshot_after_sha256)
        if after.run != receipt.run or after.pack_sha256 != receipt.pack_sha256:
            raise WorkflowError("identity_mismatch")
        try:
            canonical: str | None = spec.schema.model_validate_json(filled).content_hash()
        except ValueError:
            canonical = None
        if canonical != submission.canonical_review_sha256:
            raise WorkflowError("identity_mismatch")
        if submission.disposition == "refused":
            if (
                not issues
                or submission.issues != issues
                or after.content_hash() != binding.binding.snapshot_sha256
                or submission.step_sha256 is not None
                or submission.step_output_sha256 is not None
            ):
                raise WorkflowError("identity_mismatch")
            continue
        if issues:
            raise WorkflowError("identity_mismatch")
        # The journaled rules (`ToolRules`, or the owner core's `RULES`) at the same evidence.
        journaled = (
            _journaled_issues(binding.binding.module_id, spec.step_id, filled, evidence)
            if spec.rules == "journaled"
            else ()
        )
        attempt = _attempt_of(after, binding.binding.ticket_id)
        before_attempt = _attempt_of(historical.read(), binding.binding.ticket_id)
        candidates = (
            attempt.steps
            if len(attempt.steps) > len(before_attempt.steps)
            else attempt.step_repairs[len(before_attempt.step_repairs) :]
        )
        matches = [s for s in candidates[-1:] if s.content_hash() == submission.step_sha256]
        if (
            len(matches) != 1
            or matches[0].payload_sha256 != submission.stored_payload_sha256
            or matches[0].output_sha256 != submission.step_output_sha256
        ):
            raise WorkflowError("identity_mismatch")
        step = matches[0]
        result: Module | None = None
        if submission.disposition == "valid":
            if step.status != "valid" or submission.issues or journaled:
                raise WorkflowError("identity_mismatch")
            valid.append((attempt.ticket_id, step.step_id, step.content_hash()))
            settled = attempt.status == "finished"
        else:
            if step.issues != submission.issues:
                raise WorkflowError("identity_mismatch")
            result = _verify_invalid_step(
                store,
                historical,
                spec,
                binding.binding,
                _raw(store, binding.payload_sha256),
                attempt,
                step,
                journaled,
            )
            settled = result is not None
        if settled:
            if attempt.ticket_id in settlements:
                raise WorkflowError("identity_mismatch")
            settlements[attempt.ticket_id] = _Settlement(attempt, result)
    return valid, settlements


def _verify_settlements(
    store: Execution,
    snapshot: ExecutionSnapshot,
    settlements: Mapping[str, _Settlement],
    analytical: tuple[str, ...],
) -> list[tuple[str, str, str]]:
    """R5-1: the final snapshot holds every finished analytical attempt exactly as the submission
    that settled it left it, and no other finished one. Every analytical head is such an
    attempt's result: a blocked head is the rebuilt invalid-step settlement of attempt 1 (issues,
    an invalid last step); any other head is a valid settlement its module's probe re-settles on
    the final snapshot, and no valid settlement sits outside a head. Every analytical head's
    attempt was begun on the inputs the final snapshot binds for its module (R6-1). Returns the
    steps of every probed head attempt; each needs a valid submission."""
    finished = {
        a.ticket_id: a
        for a in snapshot.attempts
        if a.module_id in analytical and a.status == "finished"
    }
    if set(finished) != set(settlements) or any(
        finished[ticket] != settlement.attempt for ticket, settlement in settlements.items()
    ):
        raise WorkflowError("identity_mismatch")
    probed: set[str] = set()
    expected: list[tuple[str, str, str]] = []
    for head in snapshot.heads:
        if head.module_id not in analytical:
            continue
        attempt = _result_attempt(snapshot, head)
        settlement = settlements.get(attempt.ticket_id)
        if settlement is None:
            raise WorkflowError("identity_mismatch")
        # R6-1: the head's attempt was begun on exactly the inputs the final snapshot binds for
        # its module. A CP-0 head that no longer commands this consumer (NotAuthorized) or an
        # upstream the final snapshot does not bind (any other ValueError) is a forgery, not a
        # pass: both map to identity_mismatch explicitly.
        try:
            bound = current_inputs(snapshot, head.module_id)
        except NotAuthorized:
            raise WorkflowError("identity_mismatch") from None
        except ValueError:
            raise WorkflowError("identity_mismatch") from None
        if bound != attempt.inputs:
            raise WorkflowError("identity_mismatch")
        if head.status == "blocked":
            if (
                settlement.result is None
                or attempt.number != 1
                or not attempt.issues
                or not attempt.steps
                or attempt.steps[-1].status != "invalid"
                or head != head_of(settlement.result)
            ):
                raise WorkflowError("identity_mismatch")
            continue
        if settlement.result is not None or attempt.issues:
            raise WorkflowError("identity_mismatch")
        _PROBES[head.module_id](store, snapshot, attempt)
        probed.add(attempt.ticket_id)
        expected += [(attempt.ticket_id, s.step_id, s.content_hash()) for s in attempt.steps]
    if any(s.result is None and ticket not in probed for ticket, s in settlements.items()):
        raise WorkflowError("identity_mismatch")
    return expected


def _verify(
    store: Execution,
    receipt: OwnerRunReceipt,
    *,
    publication_directory: Path | None,
    sealed: bool,
) -> None:
    snapshot = store.read()
    if (snapshot.run, snapshot.pack_sha256, snapshot.content_hash()) != (
        receipt.run,
        receipt.pack_sha256,
        receipt.snapshot_sha256,
    ):
        raise WorkflowError("stale_binding")
    store.pack(snapshot)
    planned = plan(snapshot.run.requested_modules)
    # A run `create` could not have opened (a planned module without a spec) is evidence that
    # does not bind (R4-4), not a raw lookup failure.
    if receipt.plan != planned or any(m not in OWNER_SPECS for m in planned):
        raise WorkflowError("identity_mismatch")
    analytical = tuple(m for m in planned if OWNER_SPECS[m].kind == "analytical")
    deterministic = next((m for m in planned if OWNER_SPECS[m].kind == "deterministic"), None)
    if len(receipt.heads) != len(snapshot.heads) or {h.module_id for h in snapshot.heads} != {
        h.module_id for h in receipt.heads
    }:
        raise WorkflowError("identity_mismatch")
    for head in snapshot.heads:
        if head != head_of(store.head_module(head), _QUALIFICATION.get(head.module_id)):
            raise WorkflowError("identity_mismatch")
        if _settled(store, head.module_id) not in receipt.heads:
            raise WorkflowError("identity_mismatch")
    # A sealed run holds no begun, never finished attempt (S1a adv-4 LOW 1).
    if any(a.status == "pending" for a in snapshot.attempts):
        raise WorkflowError("identity_mismatch")
    # The deterministic head binds the final snapshot's inputs, as an analytical one does in
    # `_verify_settlements` (S1a adv-4 MEDIUM 1): the same explicit exception mapping.
    for head in snapshot.heads:
        if head.module_id != deterministic:
            continue
        try:
            bound = current_inputs(snapshot, head.module_id)
        except NotAuthorized:
            raise WorkflowError("identity_mismatch") from None
        except ValueError:
            raise WorkflowError("identity_mismatch") from None
        if bound != _result_attempt(snapshot, head).inputs:
            raise WorkflowError("identity_mismatch")
    retained = Counter(
        (a.ticket_id, s.content_hash())
        for a in snapshot.attempts
        if a.module_id in analytical
        for s in (*a.steps, *a.step_repairs)
    )
    recorded = Counter(
        (s.binding.binding.ticket_id, s.step_sha256)
        for s in receipt.submissions
        if s.disposition != "refused"
    )
    if retained != recorded:
        raise WorkflowError("identity_mismatch")
    # R6-2: every attempt and head in every snapshot of the run is a planned module, and the only
    # non-analytical one is the planned deterministic module.
    allowed = frozenset(analytical) | frozenset(() if deterministic is None else (deterministic,))
    ancestors = set()
    chain: list[ExecutionSnapshot] = []
    cursor = snapshot
    while True:
        digest = cursor.content_hash()
        if (
            digest in ancestors
            or cursor.run != receipt.run
            or cursor.pack_sha256 != receipt.pack_sha256
            or any(a.module_id not in allowed for a in cursor.attempts)
            or any(h.module_id not in allowed for h in cursor.heads)
        ):
            raise WorkflowError("identity_mismatch")
        ancestors.add(digest)
        chain.append(cursor)
        if cursor.parent is None:
            break
        cursor = _snapshot(store, cursor.parent)
    chain.reverse()
    bindings = (
        [c.binding for c in receipt.calls]
        + [r.binding for r in receipt.input_reads]
        + [s.binding.binding for s in receipt.submissions]
    )
    coordinates = [b.snapshot_sha256 for b in bindings]
    coordinates += [s.snapshot_after_sha256 for s in receipt.submissions]
    coordinates += [r.snapshot_sha256 for r in receipt.refusals]
    coordinates += [
        x for b in receipt.begins for x in (b.snapshot_before_sha256, b.snapshot_after_sha256)
    ]
    coordinates += [
        x for p in receipt.publications for x in (p.snapshot_before_sha256, p.snapshot_after_sha256)
    ]
    if any(digest not in ancestors for digest in coordinates):
        raise WorkflowError("identity_mismatch")
    if (
        sealed
        and (store.directory / AUDIT / "receipt.sha256").read_text() != receipt.content_hash()
    ):
        raise WorkflowError("identity_mismatch")
    _verify_audit(store, receipt)
    _verify_begins(store, receipt, frozenset(analytical))
    _verify_attempts(snapshot, receipt, frozenset(analytical))
    _verify_walk(store, receipt, analytical, planned, deterministic)
    # Terminal is a property of the snapshot the publication started from: heads that settle
    # after the stop cannot alter it.
    stop = (
        _snapshot(store, receipt.publications[0].snapshot_before_sha256)
        if (deterministic is not None and receipt.publications)
        else snapshot
    )
    terminal = deterministic is not None and _terminal(stop.heads, stop.run, deterministic)
    _verify_publications(store, receipt, terminal, deterministic)
    _verify_chain(receipt, chain, deterministic, planned)
    _verify_calls_reads(store, receipt, OWNER_SPECS)
    valid, settlements = _verify_submissions(store, receipt, OWNER_SPECS)
    expected_steps = _verify_settlements(store, snapshot, settlements, analytical)
    if not all(item in valid for item in expected_steps):
        raise WorkflowError("identity_mismatch")
    _verify_publication_outcome(
        store, snapshot, receipt, publication_directory, terminal, deterministic
    )
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise WorkflowError("stale_binding")


def _verify_publication_outcome(
    store: Execution,
    snapshot: ExecutionSnapshot,
    receipt: OwnerRunReceipt,
    directory: Path | None,
    terminal: bool,
    deterministic: str | None,
) -> None:
    if deterministic is None:
        if directory is not None:
            raise WorkflowError("identity_mismatch")
        return
    if receipt.model is None:
        publication = receipt.publications[0] if len(receipt.publications) == 1 else None
        if (
            not terminal
            or directory is not None
            or publication is None
            or any(a.module_id == deterministic for a in snapshot.attempts)
            or any(h.module_id == deterministic for h in snapshot.heads)
        ):
            raise WorkflowError("identity_mismatch")
        with tempfile.TemporaryDirectory() as refused_directory:
            stop = _snapshot(store, publication.snapshot_before_sha256)
            try:
                publish_cp_model(
                    _FrozenExecution(store, stop), output=Path(refused_directory) / "absent"
                )
            except CpModelRefused as error:
                expected = PublicationCall(
                    snapshot_before_sha256=stop.content_hash(),
                    snapshot_after_sha256=stop.content_hash(),
                    status="refused",
                    reason=str(error),
                    ticket_id=None,
                    files={},
                )
                if publication != expected:
                    raise WorkflowError("identity_mismatch") from None
            else:
                raise WorkflowError("identity_mismatch")
        return
    # R4-4: a recorded publication without the heads it names is a tamper cause, checked here
    # before `financial_workflow._record` looks them up.
    if not {deterministic, "CP-1"} <= {h.module_id for h in snapshot.heads}:
        raise WorkflowError("identity_mismatch")
    model = _record(store, deterministic)
    if (
        terminal
        or directory is None
        or set(receipt.model.files) != set(FILES)
        or _files(directory) != receipt.model.files
        or (model.ticket_id, model.result_sha256, _record(store, "CP-1").result_sha256)
        != (receipt.model.ticket_id, receipt.model.result_sha256, receipt.model.cp1_result_sha256)
        or verify_cp_model_publication(store, directory)
    ):
        raise WorkflowError("identity_mismatch")
    _verify_model_settlement(store, snapshot, directory)
    last = receipt.publications[-1]
    if (
        last.status != "published"
        or last.ticket_id != model.ticket_id
        or last.files != receipt.model.files
    ):
        raise WorkflowError("identity_mismatch")
    # Later modules may have settled since: the publication's `after` is an ancestor (the chain
    # check anchors it) and holds the same CP-MODEL head as the final snapshot.
    published = _snapshot(store, last.snapshot_after_sha256)
    if next((h for h in published.heads if h.module_id == deterministic), None) != next(
        (h for h in snapshot.heads if h.module_id == deterministic), None
    ):
        raise WorkflowError("identity_mismatch")


def verify_owner_run_receipt(
    store: Execution, receipt: OwnerRunReceipt, *, publication_directory: Path | None = None
) -> None:
    """Authenticate sealed participation evidence read-only. Every submission is replayed at its
    historical snapshot (R4-2), every settlement rebuilt and bound to the final snapshot (R5-1),
    the recorded coordinates form one gapless chain of own-ticket transitions from the created
    snapshot to the final one and every head binds the final snapshot's inputs (R6-1), and only
    planned modules appear anywhere in it (R6-2); every begin is what `Execution.begin` yields on
    its `before` (Stage 4 class A); nothing is written.

    Known gap (Stage 4 class D, ruling D1; `docs/G1X-OWNER-CORE-PROTOCOL.md` section 4): refused
    submissions and refused calls after a binding's last submit change no snapshot, so their
    presence, completeness and order are not anchored; each record given is checked, the set is
    not. Nothing a head, attempt, input or publication depends on is affected.

    Exception mapping (S1a R4-4, as B1 N2): a tamper cause refuses `identity_mismatch`. Those are
    evidence that fails to parse or to hash (`ValueError`: pydantic, JSON, UTF-8, the store's
    blob and snapshot checks, the core refusals) and evidence that is missing or unreadable
    (`OSError`); every lookup a forged record can reach is an explicit check. Programming errors
    (`TypeError`, `KeyError`, `StopIteration`, `AttributeError`, ...) propagate unchanged."""
    try:
        receipt = OwnerRunReceipt.model_validate_json(receipt.model_dump_json())
        _verify(store, receipt, publication_directory=publication_directory, sealed=True)
    except WorkflowError:
        raise
    except (ValueError, OSError):
        raise WorkflowError("identity_mismatch") from None


def serve_json_lines(
    workflow: OwnerWorkflow,
    reader: TextIO,
    writer: TextIO,
    *,
    destination: Path,
    participant: str,
) -> None:
    if workflow._calls or workflow._submissions or workflow._reads:
        raise WorkflowError("not_permitted")
    workflow._participant, workflow._transport = participant, "bounded-json-lines/1"
    _retain(workflow._store, "transport", TransportMarker(participant=participant))
    for _ in range(MAX_MESSAGES):
        line = reader.readline(MAX_LINE + 1)
        if not line:
            return
        try:
            if len(line) > MAX_LINE or not line.endswith("\n"):
                while line and not line.endswith("\n"):
                    line = reader.readline(MAX_LINE + 1)
                raise WorkflowError("bad_arguments")
            request = json.loads(line, parse_constant=_nonfinite_json)
            if type(request) is not dict:
                raise WorkflowError("bad_arguments")
            operation = request.get("operation")
            if operation == "invoke" and set(request) == {"operation", "tool", "arguments"}:
                result = workflow.invoke(request["tool"], request["arguments"])
            elif operation == "submit_review" and set(request) == {"operation", "payload"}:
                result = workflow.submit_review(request["payload"])
            elif operation == "read_inputs" and set(request) == {"operation"}:
                result = workflow.read_inputs()
            elif operation == "publish" and set(request) == {"operation"}:
                result = workflow.publish()
            elif operation == "write_receipt" and set(request) == {"operation"}:
                receipt = workflow.write_receipt(destination)
                result = {
                    "status": "ok",
                    "receipt_sha256": receipt.content_hash(),
                    "snapshot_sha256": receipt.snapshot_sha256,
                }
            else:
                raise WorkflowError("not_permitted")
        except (WorkflowError, SourceError) as error:
            result = {"status": "refused", "error_code": error.code}
        except (ValueError, TypeError, KeyError, UnicodeError):
            result = {"status": "refused", "error_code": "bad_arguments"}
        except Exception:  # noqa: BLE001 - sanitized bounded analytical transport (as the financial slice)
            result = {"status": "error", "error_code": "internal_error"}
        writer.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
        writer.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded offline owner workflow")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--publication-directory", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--participant", required=True)
    args = parser.parse_args()
    pack = PreparedPack.model_validate_json(args.pack.read_bytes())
    workflow = OwnerWorkflow.create(
        args.directory, pack, publication_directory=args.publication_directory
    )
    serve_json_lines(
        workflow, sys.stdin, sys.stdout, destination=args.receipt, participant=args.participant
    )


if __name__ == "__main__":
    main()
