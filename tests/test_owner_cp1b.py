"""CP-1B as an owner-only core on the owner path (Part B O1, Task 3, G1c).

The registration, pair, view and composition tests are fast: they read the literal CP-1 register
of `test_earnings.fixture()` (the A1 oracle values of `cases/earnings/expected.json`) through a
read-only stand-in for the store. The two settlement tests need a real CP-1 promotion
(11-26 minutes), so they run only under `RUN_PROMOTION=1`; a failure there is a finding.
"""

import datetime as dt
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_earnings as a1
from pydantic import ValidationError

from deploy_vii.contracts import Fact, Input, Module, Run
from deploy_vii.execution import Attempt, StepSubmission
from deploy_vii.preparation import PreparedPack
from deploy_workflow import earnings_workflow as ew
from deploy_workflow import host
from deploy_workflow import owner_workflow as owner
from deploy_workflow.earnings import build_earnings_delta
from deploy_workflow.owners import cp1b
from deploy_workflow.workflow import WorkflowError

ROOT = Path(__file__).resolve().parents[1]
ORACLE = json.loads((ROOT / "cases/earnings/expected.json").read_text())
PUBLISHED_PLAN = ("CP-0", "CP-1", "CP-1B", "CP-MODEL", "CP-1D", "CP-5")

promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred"
)


def review(
    prior: str, current: str, comparison: str = "flat_sequential"
) -> cp1b.EarningsDeltaOwnerReview:
    return cp1b.EarningsDeltaOwnerReview(
        prior_period_id=prior,
        current_period_id=current,
        comparison_assessment=comparison,  # type: ignore[arg-type]
        driver_assessment="not_supplied",
        guidance_assessment="not_supplied",
    )


# --- registration --------------------------------------------------------------------------


def test_owner_only_includes_unshared_chain() -> None:
    assert owner._owner_only("CP-1B") is True  # a registered chain that is not shared-live
    assert owner._owner_only("CP-3") is False  # a shared-live chain
    assert owner._owner_only("CP-MODEL") is True  # no chain
    assert owner._sequence("CP-1B") == ("earnings_delta",)
    owner._check_steps("CP-1B", owner.OWNER_SPECS["CP-1B"])


def test_cp1b_rows_are_registered() -> None:
    spec = owner.OWNER_SPECS["CP-1B"]
    assert spec.entry == "owner_core" and spec.kind == "analytical" and spec.publish is None
    (item,) = spec.steps
    assert item.step_id == "earnings_delta" and item.schema is cp1b.EarningsDeltaOwnerReview
    assert item.inputs == "module_context" and not item.sources and item.rules == "none"
    assert item.upstream_grant is None and not item.extract
    assert owner._CORES["CP-1B"] is cp1b
    assert "CP-1B" in owner.SUPPORTED_ANALYTICAL
    assert owner._QUALIFICATION["CP-1B"] is cp1b.QUALIFICATION
    assert owner._PROBES["CP-1B"] is cp1b.probe
    assert owner._ENTRY_VALIDATORS["CP-1B"] is cp1b.ENTRY_VALIDATOR
    assert owner._VIEWS["earnings_delta"] is cp1b.view
    assert ("CP-1B", "earnings_delta") not in host._OWNER_SCOPES  # no sources
    assert not hasattr(cp1b, "RULES")
    assert host._submission_schema("CP-1B", "earnings_delta") is cp1b.EarningsDeltaOwnerReview


def test_check_specs_admits_earnings_update(tmp_path: Path) -> None:
    run = Run(
        run_id="r1",
        issuer_id="i1",
        issuer_name="I",
        as_of=dt.date(2026, 1, 1),
        case_kind="synthetic",
        pathway="earnings_update",
    )
    pack = PreparedPack(run=run, sources=())
    planned = owner._check_specs(pack, owner.OWNER_SPECS, tmp_path / "pub", tmp_path / "ex")
    assert planned == PUBLISHED_PLAN


def test_submission_shape_is_two_period_ids_and_three_literals() -> None:
    assert set(cp1b.EarningsDeltaOwnerReview.model_fields) == {
        "prior_period_id",
        "current_period_id",
        "comparison_assessment",
        "driver_assessment",
        "guidance_assessment",
    }
    bad_fields: tuple[dict[str, Any], ...] = (
        {"driver_assessment": "supplied"},
        {"comparison_assessment": "anything"},
        {"selections": []},
    )
    for bad in bad_fields:
        document = {
            "prior_period_id": "q3-2025",
            "current_period_id": "q4-2025",
            "comparison_assessment": "flat_sequential",
            "driver_assessment": "not_supplied",
            "guidance_assessment": "not_supplied",
            **bad,
        }
        with pytest.raises(ValidationError):
            cp1b.EarningsDeltaOwnerReview.model_validate_json(json.dumps(document))
    issues = cp1b._parsed("[1]")[1]
    assert issues and cp1b._parsed("{}")[0] is None


# --- the pair rule --------------------------------------------------------------------------


def test_cp1b_pair_rule_accepts_what_the_delta_core_accepts() -> None:
    module = _register()
    flat = cp1b.compute(module, review("q3-2025", "q4-2025"))
    assert flat.issues == () and flat.report is not None
    assert tuple(p.measure_id for p in flat.report.points) == a1.MEASURES
    for point, expected in zip(flat.report.points, ORACLE["positive"]["points"], strict=True):
        assert point.delta == (None if expected["delta"] is None else Decimal(expected["delta"]))
        assert point.delta_status == expected["delta_status"]
    no_yoy = cp1b.compute(module, review("fy-2024", "fy-2025", "comparative_not_supplied"))
    assert no_yoy.issues == () and no_yoy.report is not None
    assert no_yoy.report.prior_basis_id is None
    assert no_yoy.report.points[0].current_value == Decimal(ORACLE["gap"]["current_revenue"])


def test_cp1b_assessment_must_be_the_one_python_derives() -> None:
    module = _register()
    wrong_flat = cp1b.compute(module, review("fy-2024", "fy-2025", "flat_sequential"))
    assert wrong_flat.report is None and "comparative_not_supplied" in wrong_flat.issues[0]
    wrong_gap = cp1b.compute(module, review("q3-2025", "q4-2025", "comparative_not_supplied"))
    assert wrong_gap.report is None and "flat_sequential" in wrong_gap.issues[0]


@pytest.mark.parametrize(
    ("prior", "current", "code"),
    [
        ("q4-2025", "q3-2025", "incompatible_periods"),
        ("q4-2025", "q4-2025", "incompatible_periods"),
        ("fy-2025", "q4-2025", "incompatible_periods"),
        ("q3-2025", "no-such-period", "incomplete_register"),
    ],
)
def test_cp1b_pairs_the_core_refuses_are_issues_named_by_its_code(
    prior: str, current: str, code: str
) -> None:
    found = cp1b.compute(a1.fixture(), review(prior, current))
    assert found.report is None and found.issues == (code,)


def test_cp1b_a_view_that_is_not_cp1_is_charged_invalid_source_view() -> None:
    wrong = a1.fixture().model_copy(update={"module_id": "CP-2"})
    assert cp1b.compute(wrong, review("q3-2025", "q4-2025")).issues == ("invalid_source_view",)


# --- B19: only the pairs the composer's fixed prose is true of --------------------------------


def _moved(facts: tuple[Any, ...], fact_id: str, amount: str) -> tuple[Any, ...]:
    assert sum(f.fact_id == fact_id for f in facts) == 1
    return tuple(
        f.model_copy(update={"amount": Decimal(amount)}) if f.fact_id == fact_id else f
        for f in facts
    )


def _with_period(
    module: Any, pid: str, kind: str, quarter: str | None, start: str, end: str
) -> Any:
    """A copy of the literal register with one more period row, values copied from q4-2025."""
    fields = dict(
        zip(
            a1.PERIOD_FIELDS,
            (
                pid,
                kind,
                end[:4],
                quarter,
                start,
                end,
                "USD",
                "MILLIONS",
                "IFRS",
                "consolidated group",
            ),
            strict=True,
        )
    )
    source = {f.field: f for f in module.facts if f.row_id == "period.q4-2025"}
    added = [
        source[name].model_copy(
            update={
                "fact_id": f"period.{pid}.{name}",
                "row_id": f"period.{pid}",
                "text": value,
                "period": pid,
                "status": "not_applicable" if value is None else "known",
            }
        )
        for name, value in fields.items()
    ]
    basis = a1.BASES["q4-2025"]
    label = f"{pid}: {start} to {end}"
    for fact in [f for f in module.facts if f.field == basis]:
        measure = fact.row_id.removeprefix("metric.")
        added.append(
            fact.model_copy(
                update={
                    "fact_id": f"value.{measure}.{pid}",
                    "field": _basis_of(pid, kind),
                    "period": label,
                }
            )
        )
    return module.model_copy(update={"facts": (*module.facts, *added)})


def _basis_of(pid: str, kind: str) -> str:
    from deploy_workflow.earnings import _basis, _Period

    return _basis(_Period(pid, kind, dt.date(2000, 1, 1), dt.date(2000, 1, 2), {}))


@pytest.mark.parametrize(
    ("prior", "current"),
    [
        ("q2-2025", "q4-2025"),  # a period the register lacks, against a quarter
        ("q3-2025x", "q4-2025"),  # a misspelt prior
        ("q1-2026", "q4-2025"),  # a prior after the current period, not in the register
        ("q4-2024", "q4-2025"),  # a prior year, not in the register
        ("fy-2024", "q4-2025"),
    ],
)
def test_cp1b_other_pairs_are_unsupported(prior: str, current: str) -> None:
    for comparison in ("flat_sequential", "comparative_not_supplied"):
        found = cp1b.compute(a1.fixture(), review(prior, current, comparison))
        assert found.report is None and found.issues == ("unsupported_pair",), comparison


def test_cp1b_q2_prior_is_not_labelled_fy2024() -> None:
    """Reviewer case A: q2-2025 -> q4-2025 used to settle with the FY2024/FY2025 prose."""
    found = cp1b.compute(a1.fixture(), review("q2-2025", "q4-2025", "comparative_not_supplied"))
    assert found.issues == ("unsupported_pair",)


def test_cp1b_non_flat_quarter_pair_is_unsupported() -> None:
    """Reviewer case B: revenue 30 -> 45 is not flat, and the prose says "is flat"."""
    module = a1.fixture()
    moved = module.model_copy(update={"facts": _moved(module.facts, "value.revenue.q4-2025", "45")})
    found = cp1b.compute(moved, review("q3-2025", "q4-2025"))
    assert found.report is None and found.issues == ("unsupported_pair",)


def test_cp1b_q4_2024_present_is_still_unsupported() -> None:
    module = _with_period(a1.fixture(), "q4-2024", "QUARTER", "4", "2024-10-01", "2024-12-31")
    found = cp1b.compute(module, review("q4-2024", "q4-2025"))
    assert found.report is None and found.issues == ("unsupported_pair",)


def test_cp1b_prior_year_period_in_the_register_falsifies_the_limits() -> None:
    """The limitation "no FY2024 annual income statement or prior-year quarterly series is
    supplied" is true only while the register carries none, so the pair is refused."""
    module = _with_period(a1.fixture(), "q4-2024", "QUARTER", "4", "2024-10-01", "2024-12-31")
    for prior, current, comparison in (
        ("q3-2025", "q4-2025", "flat_sequential"),
        ("fy-2024", "fy-2025", "comparative_not_supplied"),
    ):
        found = cp1b.compute(module, review(prior, current, comparison))
        assert found.issues == ("unsupported_pair",), (prior, current)


def test_cp1b_comparison_label_is_derived_from_the_deltas() -> None:
    module = _register()
    flat = cp1b.compute(module, review("q3-2025", "q4-2025")).report
    gap = cp1b.compute(module, review("fy-2024", "fy-2025", "comparative_not_supplied")).report
    assert flat is not None and gap is not None
    assert cp1b.expected_comparison(flat) == "flat_sequential"
    assert cp1b.expected_comparison(gap) == "comparative_not_supplied"
    moved = module.model_copy(update={"facts": _moved(module.facts, "value.revenue.q4-2025", "45")})
    raw = build_earnings_delta(moved, "q3-2025", "q4-2025")
    with pytest.raises(ValueError, match="unsupported_pair"):
        cp1b.expected_comparison(raw)


def test_cp1b_owner_limits_state_nothing_the_path_cannot_know() -> None:
    """The owner head carries no "Unaudited" claim (the delta core checks the dimensions, not the
    audit status) and no checkpoint line."""
    for prior, current, comparison in (
        ("q3-2025", "q4-2025", "flat_sequential"),
        ("fy-2024", "fy-2025", "comparative_not_supplied"),
    ):
        outcome, _, _ = _validate(_payload(prior, current, comparison))
        assert outcome.output is not None
        owned = Module.model_validate_json(outcome.output)
        assert owned.limitations and not any("naudited" in x for x in owned.limitations)
        assert not any("Owner checkpoint" in x for x in owned.limitations)


# --- the guards follow the real E-* register (fix 2) ---------------------------------------------

_OPENING = {
    "period_id": "opening-2024",
    "fiscal_year": "2024",
    "fiscal_quarter": None,
    "period_type": "PERIOD_END",
    "start_date": None,
    "end_date": "2024-12-31",
    "day_count": None,
    "audit_status": "unaudited",
    "currency": "USD",
    "unit": "MILLIONS",
    "accounting_basis": "IFRS",
    "entity_perimeter": "consolidated group",
    "source_id": "financial",
    "source_locator": "page:1",
    "component_period_ids": None,
}


def _with_opening(module: Any) -> Any:
    """The literal register plus the `opening-2024` PERIOD_END row the real E-* CP-1 holds
    (tests/test_earnings.py `test_canonical_opening_period_end_is_indexed_...`)."""
    citation = module.facts[0].citations
    rows = tuple(
        Fact(
            fact_id=f"opening-2024.{field}",
            label=field,
            table_id="T4.14",
            row_id="opening-2024",
            field=field,
            text=value,
            status="known"
            if value is not None
            else "not_applicable"
            if field in {"fiscal_quarter", "component_period_ids"}
            else "missing",
            limitation=None if value is not None else "Source does not supply this field",
            period="opening-2024",
            basis="IFRS · consolidated group",
            citations=citation,
        )
        for field, value in _OPENING.items()
    )
    return module.model_copy(update={"facts": (*module.facts, *rows)})


def _register() -> Any:
    """The literal A1 register with the real E-* register's opening-2024 row."""
    return _with_opening(a1.fixture())


def _compute_pair(module: Any, prior: str, current: str, comparison: str) -> Any:
    return cp1b.compute(module, review(prior, current, comparison))


def test_cp1b_both_pairs_settle_on_the_real_register_shape() -> None:
    module = _with_opening(a1.fixture())
    assert _compute_pair(module, "q3-2025", "q4-2025", "flat_sequential").issues == ()
    gap = _compute_pair(module, "fy-2024", "fy-2025", "comparative_not_supplied")
    assert gap.issues == () and gap.report is not None


def test_cp1b_gap_pair_needs_the_opening_2024_row_its_limit_names() -> None:
    """ "Opening-2024 balance data exists" must be true wherever the gap pair settles."""
    found = _compute_pair(a1.fixture(), "fy-2024", "fy-2025", "comparative_not_supplied")
    assert found.report is None and found.issues == ("unsupported_pair",)


def test_cp1b_gap_pair_needs_known_fy_leverage() -> None:
    module = _with_opening(a1.fixture())
    lost = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"amount": None, "status": "missing", "limitation": "x"})
                if f.fact_id == "value.total_leverage_reported.fy-2025"
                else f
                for f in module.facts
            )
        }
    )
    found = _compute_pair(lost, "fy-2024", "fy-2025", "comparative_not_supplied")
    assert found.report is None and found.issues == ("unsupported_pair",)


def test_cp1b_flat_pair_needs_the_four_quarter_reason_for_missing_q3_leverage() -> None:
    module = a1.fixture()
    other = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"limitation": "Source does not supply it"})
                if f.fact_id.startswith("value.")
                and f.fact_id.endswith(".q3-2025")
                and f.status == "missing"
                else f
                for f in module.facts
            )
        }
    )
    found = _compute_pair(other, "q3-2025", "q4-2025", "flat_sequential")
    assert found.report is None and found.issues == ("unsupported_pair",)


# --- the split composer keeps the receipt path's bytes ----------------------------------------

# sha256 of `EarningsWorkflow._compose(...).model_dump_json()` on the literal register, taken at
# dbcfbadb~1 (before the composer split) by mx-precise's probe_byte_identity.py
# (scratchpad/o1t3-review/probe_byte_identity.py) with these inputs.
PRE_SPLIT_COMPOSED = {
    ("q3-2025", "q4-2025"): "82661619fdd206dcaf64e2781659ab5300ce50b5763048524a18c3c2d85a88f4",
    ("fy-2024", "fy-2025"): "252d73fc7cd796772af792e1e370e2e99841012968d2eed307446b7677340a82",
}


@pytest.mark.parametrize("pair", sorted(PRE_SPLIT_COMPOSED))
def test_split_composer_keeps_the_pre_split_bytes(pair: tuple[str, str]) -> None:
    producer = _producer(opening=False)  # the register the pins were taken on
    attempt = _attempt(producer)
    prior, current = pair
    report = build_earnings_delta(cp1b.cp1_view(producer), prior, current)
    selections = tuple(
        ew.MeasureSelection(
            measure_id=p.measure_id,
            prior_fact_id=p.prior_fact_id,
            current_fact_id=p.current_fact_id,
            companion_fact_ids=p.companion_fact_ids,
        )
        for p in report.points
    )
    derived = ew.EarningsDeltaReview(
        prior_period_id=prior,
        current_period_id=current,
        selections=selections,
        comparison_assessment=cp1b.expected_comparison(report),  # type: ignore[arg-type]
        driver_assessment="not_supplied",
        guidance_assessment="not_supplied",
    )
    binding = ew.OwnerBinding(
        run_id=_run().run_id,
        issuer_id=_run().issuer_id,
        as_of="2026-01-01",
        method_version="deploy-v-r14",
        pack_sha256="c" * 64,
        snapshot_sha256="d" * 64,
        module_id="CP-1B",
        step_id="earnings_delta",
        ticket_id="t1",
        attempt=0,
        inputs=attempt.inputs,
    )
    participation = ew.EarningsParticipation(
        binding=binding,
        session_id="s1",
        grant_sha256="e" * 64,
        manifest_sha256="e" * 64,
        access_read_sha256="e" * 64,
        call_ids=(),
        successful_call_ids=(),
        manifest_call_ids=(),
        period_lookup_call_ids=(),
        metric_lookup_call_ids=(),
        citation_call_ids=(),
    )
    composed = ew._compose(
        producer, report, ew._operands(producer, report), derived, participation, attempt, _run()
    )
    assert (
        hashlib.sha256(composed.model_dump_json().encode()).hexdigest()
        == (PRE_SPLIT_COMPOSED[pair])
    )


# --- the view, the validator and the candidate -----------------------------------------------


class _Store:
    """A read-only stand-in for the store: the two reads the core makes (`result`, `payload`)."""

    def __init__(self, producer: Module, payload: str) -> None:
        self.producer, self._payload = producer, payload

    def result(self, sha256: str) -> Module:
        assert sha256 == self.producer.content_hash()
        return self.producer

    def payload(self, sha256: str) -> str:
        assert sha256 == "b" * 64
        return self._payload


def _producer(opening: bool = False) -> Module:
    source = _register() if opening else a1.fixture()
    return Module(
        run_id="slice-cp1b-flat-v1",
        issuer_id="northbridge",
        as_of=dt.date(2026, 1, 1),
        module_id="CP-1",
        status="restricted",
        facts=source.facts,
        limitations=source.limitations,
    )


def _attempt(producer: Module, step: StepSubmission | None = None) -> Attempt:
    steps = () if step is None else (step,)
    return Attempt(
        ticket_id="t1",
        module_id="CP-1B",
        inputs=(Input(input_id="CP-1", sha256=producer.content_hash(), status="restricted"),),
        number=0,
        steps=steps,
    )


def _run() -> Run:
    return Run(
        run_id="slice-cp1b-flat-v1",
        issuer_id="northbridge",
        issuer_name="Northbridge",
        as_of=dt.date(2026, 1, 1),
        case_kind="synthetic",
        pathway="earnings_update",
    )


def test_cp1b_view_offers_periods_and_the_accepted_pairs() -> None:
    producer = _producer(opening=True)
    sha, text = cp1b.view(_Store(producer, ""), _attempt(producer))  # type: ignore[arg-type]
    body = json.loads(text)
    assert [p["period_id"] for p in body["periods"]] == [
        "q3-2025",
        "q4-2025",
        "fy-2025",
        "opening-2024",
    ]
    assert [(p["prior_period_id"], p["current_period_id"]) for p in body["pairs"]] == [
        ("q3-2025", "q4-2025"),
        ("fy-2024", "fy-2025"),
    ]
    assert body["pairs"][1]["comparison_assessment"] == "comparative_not_supplied"
    pair = body["pairs"][0]
    assert pair["comparison_assessment"] == "flat_sequential"
    assert tuple(p["measure"] for p in pair["points"]) == a1.MEASURES
    assert pair["points"][0]["delta"] == ORACLE["positive"]["points"][0]["delta"]
    assert sha == hashlib.sha256(text.encode()).hexdigest()


def _validate(payload: str) -> Any:
    producer = _producer(opening=True)
    step = StepSubmission(step_id="earnings_delta", inputs=(), payload_sha256="b" * 64)
    attempt = _attempt(producer, step)
    pack = PreparedPack(run=_run(), sources=())
    return cp1b._validate_step(_Store(producer, payload), pack, attempt), attempt, producer  # type: ignore[arg-type]


def _payload(prior: str, current: str, comparison: str) -> str:
    return review(prior, current, comparison).model_dump_json()


def test_cp1b_validator_refuses_bad_shape_and_bad_pairs() -> None:
    assert _validate("not json")[0].issues
    assert _validate(_payload("q4-2025", "q3-2025", "flat_sequential"))[0].issues == (
        "incompatible_periods",
    )


def test_cp1b_candidate_is_the_receipt_path_candidate() -> None:
    """The shared composer: same facts, tables and claim as the receipt path composes for the
    same report; only the tail inputs and the checkpoint limitation differ."""
    outcome, attempt, producer = _validate(_payload("q3-2025", "q4-2025", "flat_sequential"))
    assert not outcome.issues and outcome.output is not None
    owned = Module.model_validate_json(outcome.output)
    report = build_earnings_delta(cp1b.cp1_view(producer), "q3-2025", "q4-2025")
    operands = ew._operands(producer, report)
    submission = review("q3-2025", "q4-2025")
    selections = tuple(
        ew.MeasureSelection(
            measure_id=p.measure_id,
            prior_fact_id=p.prior_fact_id,
            current_fact_id=p.current_fact_id,
            companion_fact_ids=p.companion_fact_ids,
        )
        for p in report.points
    )
    derived = ew.EarningsDeltaReview(
        prior_period_id=submission.prior_period_id,
        current_period_id=submission.current_period_id,
        selections=selections,
        comparison_assessment="flat_sequential",
        driver_assessment="not_supplied",
        guidance_assessment="not_supplied",
    )
    binding = ew.OwnerBinding(
        run_id="slice-cp1b-flat-v1",
        issuer_id="northbridge",
        as_of="2026-01-01",
        method_version="deploy-v-r14",
        pack_sha256="c" * 64,
        snapshot_sha256="d" * 64,
        module_id="CP-1B",
        step_id="earnings_delta",
        ticket_id="t1",
        attempt=0,
        inputs=attempt.inputs,
    )
    participation = ew.EarningsParticipation(
        binding=binding,
        session_id="s1",
        grant_sha256="e" * 64,
        manifest_sha256="e" * 64,
        access_read_sha256="e" * 64,
        call_ids=(),
        successful_call_ids=(),
        manifest_call_ids=(),
        period_lookup_call_ids=(),
        metric_lookup_call_ids=(),
        citation_call_ids=(),
    )
    receipt_path = ew._compose(producer, report, operands, derived, participation, attempt, _run())
    limits_fact = "cp1b:T1B.3:scope.limitations:assessment"  # lists the module's own limitations
    assert [f for f in owned.facts if f.fact_id != limits_fact] == [
        f for f in receipt_path.facts if f.fact_id != limits_fact
    ]
    assert owned.tables == receipt_path.tables
    assert owned.claims == receipt_path.claims
    assert owned.inputs[: len(attempt.inputs)] == attempt.inputs
    assert [i.input_id for i in owned.inputs[len(attempt.inputs) :]] == [cp1b.SUBMISSION_INPUT]
    assert owned.inputs[-1].sha256 == submission.content_hash()
    assert ew._CHECKPOINT_LIMIT in receipt_path.limitations
    assert ew._CHECKPOINT_LIMIT not in owned.limitations
    # the owner walk states only what the delta core checks: its perimeter line replaces the
    # Northbridge "Unaudited ..." line
    assert list(owned.limitations) == [
        ew._OWNER_PERIMETER_LIMIT,
        *(x for x in receipt_path.limitations[1:] if x != ew._CHECKPOINT_LIMIT),
    ]
    assert cp1b._candidate(outcome.output, attempt) == owned
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp1b._candidate(outcome.output, attempt.model_copy(update={"number": 1}))


def test_cp1b_submit_refuses_a_wrong_step_and_a_rules_argument() -> None:
    with pytest.raises(ValueError, match="one step"):
        cp1b.submit(None, "t", "other", "{}", None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="no tool-use rules"):
        cp1b.submit(None, "t", "earnings_delta", "{}", lambda text: ())  # type: ignore[arg-type]


# --- settlement on a real CP-1 promotion (deferred) -------------------------------------------


def _foundation(tmp_path: Path, case_id: str) -> Any:
    """The settled CP-1 head of `cases/earnings` (identity + financial, the bytes
    `expected.json` is frozen on) and CP-1B's pending ticket."""
    import test_earnings_workflow as host_tests

    from deploy_vii.execution import Execution

    core = host_tests.api()
    host_tests.drive_fresh_foundation(core, tmp_path / "store", case_id)
    store = Execution(tmp_path / "store")
    attempt = next(a for a in store.read().attempts if a.status == "pending")
    assert attempt.module_id == "CP-1B"
    return store, attempt


def _receipt_head(tmp_path: Path, case_id: str) -> Module:
    """The CP-1B head `EarningsWorkflow` composes for `case_id` (the frozen receipt path)."""
    import test_earnings_workflow as host_tests

    from deploy_vii.execution import Execution

    core = host_tests.api()
    workflow = host_tests.drive_fresh_foundation(core, tmp_path / "receipt-store", case_id)
    host_tests.settle_owner(core, workflow, tmp_path / "receipt.json")
    store = Execution(tmp_path / "receipt-store")
    head = next(h for h in store.read().heads if h.module_id == "CP-1B")
    return store.head_module(head)


@promotion
@pytest.mark.parametrize(
    ("case_id", "prior", "current", "comparison"),
    [
        ("E-QOQ-FLAT", "q3-2025", "q4-2025", "flat_sequential"),
        ("E-NO-YOY", "fy-2024", "fy-2025", "comparative_not_supplied"),
    ],
)
def test_cp1b_period_pairs(
    tmp_path: Path, case_id: str, prior: str, current: str, comparison: str
) -> None:
    store, attempt = _foundation(tmp_path / "owner", case_id)
    submitted = cp1b.submit(
        store, attempt.ticket_id, "earnings_delta", _payload(prior, current, comparison), None
    )
    assert submitted.journal.status == "finished" and not submitted.journal.issues
    snapshot = store.read()
    head = next((h for h in snapshot.heads if h.module_id == "CP-1B"), None)
    assert head is not None and head.status in ("accepted", "restricted")
    settled = store.head_module(head)
    owned = {f.fact_id: f for f in settled.facts}
    if case_id == "E-QOQ-FLAT":
        growth = {"revenue", "ebitda", "adjusted_ebitda"}
        for expected in ORACLE["positive"]["points"]:
            measure = expected["measure_id"]
            if measure not in a1.MEASURES[:7]:  # the T1B.1 rows
                continue
            delta = owned[f"cp1b:T1B.1:{measure}:delta"]
            assert delta.status == expected["delta_status"]
            assert delta.amount == (
                None if expected["delta"] is None else Decimal(expected["delta"])
            )
            if measure in growth:
                assert owned[f"cp1b:T1B.1:{measure}:growth"].status == expected["growth_status"]
    else:
        revenue = owned["cp1b:T1B.1:revenue:current"]
        assert revenue.amount == Decimal(ORACLE["gap"]["current_revenue"])
        assert owned["cp1b:T1B.1:revenue:prior"].status == "missing"
    assert settled.inputs[-1].input_id == "earnings-delta-submission"
    # tables and claims equal what EarningsWorkflow composes for the same case
    receipt = _receipt_head(tmp_path, case_id)
    assert settled.tables == receipt.tables
    assert settled.claims == receipt.claims
    done = next(a for a in snapshot.attempts if a.ticket_id == attempt.ticket_id)
    cp1b.probe(store, snapshot, done)  # the untampered head rebuilds


@promotion
def test_cp1b_probe_rejects_tampered_head(tmp_path: Path) -> None:
    store, attempt = _foundation(tmp_path, "E-QOQ-FLAT")
    cp1b.submit(
        store,
        attempt.ticket_id,
        "earnings_delta",
        _payload("q3-2025", "q4-2025", "flat_sequential"),
        None,
    )
    snapshot = store.read()
    done = next(a for a in snapshot.attempts if a.ticket_id == attempt.ticket_id)
    step = done.steps[0]
    module = json.loads(store.step_output(step.output_sha256 or ""))
    module["limitations"] = [*module["limitations"], "forged limitation"]
    forged_step = step.model_copy(update={"output_sha256": store._store(json.dumps(module))})
    forged_attempt = done.model_copy(update={"steps": (forged_step,)})
    forged = snapshot.model_copy(
        update={
            "attempts": tuple(
                forged_attempt if a.ticket_id == done.ticket_id else a for a in snapshot.attempts
            )
        }
    )
    with pytest.raises(WorkflowError, match="identity_mismatch"):
        cp1b.probe(store, forged, forged_attempt)
