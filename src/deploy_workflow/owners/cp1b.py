"""CP-1B (earnings update) as an owner-only core on the owner path (Part B O1, Task 3, G1c).

CP-1B has a registered step chain for its pinned step name only (`shared_live` false), so it is
served by this core (`owner_workflow._owner_only`), not by `submit_model_payload`. The analyst
names two periods and three assessments; Python reads the settled CP-1 head, builds the paired
deltas (`deploy_workflow.earnings.build_earnings_delta`, `Decimal`), derives the 12 measure
selections and composes the module with the composer the frozen `EarningsWorkflow` shares
(`earnings_workflow.compose_delta`). The step reads the CP-1 head as a `module_context` view
(no paged upstream grant, which the owner path cannot verify). The step has no pack sources, so
the core has no `RULES`.

A settled head adds one input after the attempt inputs, `earnings-delta-submission`, the content
hash of the retained submission (G1-X protocol section 2). The frozen receipt path keeps its
`earnings-review` and `earnings-participation` inputs and its checkpoint limitation; the owner
head carries neither, because it proves neither.
"""

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from deploy_vii.contracts import Contract, Identifier, Input, Module, ModuleView
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Qualification,
    StepValidation,
)
from deploy_vii.live.schema import exact_json, json_object, normalise
from deploy_vii.live.submission import Submitted
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import shape_issues
from deploy_workflow.earnings import EarningsDeltaReport, _periods, build_earnings_delta
from deploy_workflow.earnings_workflow import OwnerError, _operands, _own_limits, compose_delta
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.workflow import WorkflowError

MODULE_ID = "CP-1B"
STEP_ID = "earnings_delta"
STEP_IDS = (STEP_ID,)
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
QUALIFICATION = Qualification(implementation="implemented")

# The `build_earnings_delta` refusals a submission is charged with (the receipt path's set); any
# other `ValueError` is a defect in the register or the core and propagates.
_PERIOD_CODES = frozenset(
    {
        "incompatible_periods",
        "incomplete_register",
        "invalid_source_view",
        "incompatible_dimensions",
        "ambiguous_coordinate",
        "invalid_fact",
    }
)


class EarningsDeltaOwnerReview(Contract):
    """What the analyst submits: the period pair and the three assessments. Python derives the
    12 measure selections from the report, so no fact id is typed (ruling Q3)."""

    prior_period_id: Identifier
    current_period_id: Identifier
    comparison_assessment: Literal["flat_sequential", "comparative_not_supplied"]
    driver_assessment: Literal["not_supplied"]
    guidance_assessment: Literal["not_supplied"]


SCHEMAS: Mapping[str, type[Contract]] = {STEP_ID: EarningsDeltaOwnerReview}


@dataclass(frozen=True)
class Computation:
    """The delta report of a submission, or the issues that refuse it."""

    issues: tuple[str, ...]
    report: EarningsDeltaReport | None


UNSUPPORTED = "unsupported_pair"
FLAT_PAIR = ("q3-2025", "q4-2025")
GAP_PAIR = ("fy-2024", "fy-2025")
OPENING_2024 = "opening-2024"
FOUR_QUARTERS = "Four complete contiguous quarters"
_EARNINGS = (
    "revenue",
    "ebitda",
    "adjusted_ebitda",
    "ebitda_margin",
    "cfo_reported",
    "capex",
    "fcf",
)
_BALANCES = ("cash_closing", "total_debt", "net_debt")
_LEVERAGE = ("total_leverage_reported", "net_leverage_reported")


def _flat(report: EarningsDeltaReport) -> bool:
    """A prior exists and every T1B.1 delta is a known zero."""
    points = {p.measure_id: p for p in report.points}
    return report.prior_basis_id is not None and all(
        points[m].delta_status == "known" and points[m].delta == 0 for m in _EARNINGS
    )


def expected_comparison(report: EarningsDeltaReport) -> str:
    """The comparison label, derived from the report: no prior basis is
    `comparative_not_supplied`; a prior with every T1B.1 delta zero is `flat_sequential`. Any
    other report has no label the composer's prose is true of."""
    if report.prior_basis_id is None:
        return "comparative_not_supplied"
    if _flat(report):
        return "flat_sequential"
    raise ValueError(UNSUPPORTED)


def supported(view: ModuleView, report: EarningsDeltaReport) -> bool:
    """Whether the composer's fixed prose (and the Northbridge limitation lines) is true of this
    report (ruling B19): the flat q3-2025 -> q4-2025 pair or the missing-prior
    fy-2024 -> fy-2025 pair, with every current value known, no 2024 duration period in the register and, for the gap pair, the opening-2024 balance row
    and known FY2025 leverage; for the flat pair, Q3 leverage missing for the four-quarter reason."""
    pair = (report.prior_period_id, report.current_period_id)
    points = {p.measure_id: p for p in report.points}
    if pair not in (FLAT_PAIR, GAP_PAIR) or any(
        points[m].current_status != "known" for m in (*_EARNINGS, *_BALANCES)
    ):
        return False
    rows = _periods(view)
    # The limitations say no FY2024 or prior-year series is supplied: no 2024 duration period.
    # The `opening-2024` PERIOD_END row the real E-* register holds is a balance date, not a series.
    # Any non-PERIOD_END row (QUARTER, FY, LTM, YTD) dated 2024 is such a series.
    if any(
        r["period_type"].text != "PERIOD_END"
        and "2024" in (r["start_date"].text or "") + (r["end_date"].text or "")
        for r in rows.values()
    ):
        return False
    if pair == GAP_PAIR:
        # The table limitation "Opening-2024 balance data exists" must be true; the claim
        # "current FY2025 leverage remains valid" needs known FY2025 leverage. The opening
        # balance is evidenced by the T4.14 PERIOD_END row alone: T4.10 columns are the KPI
        # display bases of duration periods (canonical_tables._dashboard), so the register holds
        # no opening-2024 T4.10 value to require.
        opening = rows.get(OPENING_2024)
        return (
            report.prior_basis_id is None
            and opening is not None
            and opening["period_type"].text == "PERIOD_END"
            and all(points[m].current_status == "known" for m in _LEVERAGE)
        )
    # The prose says "Four complete contiguous quarters are unavailable for Q3 trailing leverage".
    return (
        _flat(report)
        and all(
            points[m].prior_status == "missing" and FOUR_QUARTERS in (points[m].reason or "")
            for m in _LEVERAGE
        )
        and all(points[m].current_status == "known" for m in _LEVERAGE)
    )


def _pair(view: ModuleView, prior: str, current: str) -> Computation:
    try:
        return Computation((), build_earnings_delta(view, prior, current))
    except ValueError as error:
        if str(error) not in _PERIOD_CODES:
            raise
        return Computation((str(error),), None)


def compute(view: ModuleView, submission: EarningsDeltaOwnerReview) -> Computation:
    """Pure: the report for the submitted pair, or the validator issues. A pair
    `build_earnings_delta` refuses is named by its `ValueError` code; an assessment other than
    the one Python derives for the pair is refused. A pair the composer's prose is not true of is
    `unsupported_pair` (ruling B19)."""
    found = _pair(view, submission.prior_period_id, submission.current_period_id)
    if found.report is None:
        return found
    if not supported(view, found.report):
        return Computation((UNSUPPORTED,), None)
    expected = expected_comparison(found.report)
    if submission.comparison_assessment != expected:
        issue = (
            f"comparison_assessment: the periods give {expected}, "
            f"not {submission.comparison_assessment}"
        )
        return Computation((issue,), None)
    return found


def cp1_view(producer: Module) -> ModuleView:
    """The bound CP-1 head as the `ModuleView` the delta core reads (as the receipt path)."""
    return ModuleView(
        module_id="CP-1",
        title="Financials",
        aliases=(),
        status=producer.status,
        artifact_sha256=producer.content_hash(),
        facts=producer.facts,
        tables=producer.tables,
        claims=producer.claims,
        limitations=(*producer.limitations, *producer.inherited_limitations),
    )


def _cp1(store: Execution, attempt: Attempt) -> Module:
    item = next((i for i in attempt.inputs if i.input_id == "CP-1"), None)
    if item is None:
        raise WorkflowError("identity_mismatch")
    return store.result(item.sha256)


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def _point_rows(report: EarningsDeltaReport) -> list[dict[str, str | None]]:
    return [
        {
            "measure": p.measure_id,
            "prior": _text(p.prior_value),
            "current": _text(p.current_value),
            "delta": _text(p.delta),
            "delta_status": p.delta_status,
            "growth": _text(p.growth),
            "growth_status": p.growth_status,
            "unit": p.unit,
        }
        for p in report.points
    ]


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of the one `read_inputs` view as compact JSON: the periods the settled CP-1
    head offers, and exactly the pairs the validator accepts (ruling B19: the flat q3-2025 ->
    q4-2025 pair and the missing-prior fy-2024 -> fy-2025 pair), each with the assessment Python
    derives and the point list it builds."""
    module = cp1_view(_cp1(historical, attempt))
    body: dict[str, object]
    try:
        rows = _periods(module)
    except ValueError as error:
        if str(error) not in _PERIOD_CODES:
            raise
        body = {"register_issue": str(error), "periods": [], "pairs": []}
    else:
        pairs: list[dict[str, object]] = []
        for prior, current in (FLAT_PAIR, GAP_PAIR):
            found = _pair(module, prior, current)
            if found.report is not None and supported(module, found.report):
                pairs.append(
                    {
                        "prior_period_id": prior,
                        "current_period_id": current,
                        "comparison_assessment": expected_comparison(found.report),
                        "points": _point_rows(found.report),
                    }
                )
        body = {
            "periods": [
                {
                    "period_id": pid,
                    "period_type": row["period_type"].text,
                    "start_date": row["start_date"].text,
                    "end_date": row["end_date"].text,
                }
                for pid, row in rows.items()
            ],
            "pairs": pairs,
        }
    text = json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode()).hexdigest(), text


def _parsed(payload: str) -> tuple[EarningsDeltaOwnerReview | None, tuple[str, ...]]:
    """The submission, or its shape issues (model text is read only through `json_object`)."""
    document = json_object(payload)
    try:
        if document is None:
            EarningsDeltaOwnerReview.model_validate_json(payload)  # for its shape issue only
            return None, ("(root): not a bounded JSON object",)
        return EarningsDeltaOwnerReview.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, shape_issues(error)


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator `submit` hands `Execution.submit_step` and the verifier replays: the
    retained output is the composed candidate, rederived from the bound CP-1 head."""
    step = attempt.steps[-1]
    submission, shape = _parsed(store.payload(step.payload_sha256))
    if submission is None:
        return StepValidation(issues=shape)
    producer = _cp1(store, attempt)
    found = compute(cp1_view(producer), submission)
    if found.report is None:
        return StepValidation(issues=found.issues)
    try:
        candidate = compose_delta(
            producer,
            found.report,
            _operands(producer, found.report),
            (Input(input_id=SUBMISSION_INPUT, sha256=submission.content_hash()),),
            _own_limits(found.report.prior_basis_id is None, owner=True),
            attempt,
            pack.run,
        )
    except OwnerError as error:
        return StepValidation(issues=(error.code,))
    return StepValidation(output=candidate.model_dump_json())


ENTRY_VALIDATOR = _validate_step


def _candidate(output: str, attempt: Attempt) -> Module:
    candidate = Module.model_validate_json(output)
    if candidate.module_id != MODULE_ID or candidate.attempt != attempt.number:
        raise WorkflowError("identity_mismatch")
    return candidate


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal the one `earnings_delta` step (null resolution through `SCHEMAS`) and, when it is
    valid, settle CP-1B with the Python candidate."""
    if step_id != STEP_ID:
        raise ValueError(f"CP-1B has one step, {STEP_ID}")
    if rules is not None:
        raise ValueError("CP-1B has no tool-use rules")
    normal, resolved = normalise(EarningsDeltaOwnerReview, payload)

    def validate(pack: PreparedPack, current: Attempt) -> StepValidation:
        return _validate_step(store, pack, current)

    attempt = store.submit_step(ticket_id, MODULE_ID, STEP_IDS, step_id, normal, validate)
    if (
        attempt.status == "pending"
        and len(attempt.steps) == 1
        and attempt.steps[0].status == "valid"
    ):
        outcome = _validate_step(store, store.pack(), attempt)
        if outcome.issues or not outcome.retained_as(attempt.steps[0]):
            raise ValueError("Retained CP-1B output differs from trusted validation")
        candidate = _candidate(outcome.output or "", attempt)
        attempt = store.finish(
            ticket_id,
            candidate.model_dump_json(),
            lambda supplied: () if supplied == candidate else ("CP-1B candidate differs",),
            qualification=QUALIFICATION,
        )
    return Submitted(attempt, normal, resolved, (), (), None)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Rerun the step validator and settlement over the settled snapshot (nothing is written);
    `WorkflowError("identity_mismatch")` unless the head rebuilds exactly."""
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)
