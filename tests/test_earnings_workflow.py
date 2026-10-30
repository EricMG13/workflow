"""Initial B1 source-only components against frozen independent expectations.

No full financial fixture is synthesized here. Owner/pager participation, all
five CP1 stages, durable recovery and downstream prefix proof need subsequent
integrated cases; these schema/factory checks do not qualify an owner execution.
Raw-wire transport cases await the explicit TextIO/byte-policy clarification.
"""

import hashlib
import importlib
import importlib.util
import inspect
import io
import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).parents[1]
CASE_MANIFEST = ROOT / "cases/earnings/manifest.json"
ORACLE = json.loads((ROOT / "cases/earnings/owner-expected.json").read_text())
CORE_ORACLE = json.loads((ROOT / "cases/earnings/expected.json").read_text())
RENDER_ORACLE = json.loads((ROOT / "cases/earnings/render-expected.json").read_text())
SOURCE = json.loads((ROOT / "cases/financial/manifest.json").read_text())
DESCRIPTOR = json.loads(CASE_MANIFEST.read_text())
TRANSPORT_ORACLE = json.loads((ROOT / "cases/earnings/transport-expected.json").read_text())
SESSION_ORACLE = json.loads((ROOT / "cases/earnings/session-binding-expected.json").read_text())
MEASURES = tuple(ORACLE["review"]["measure_order"])
EMPTY_EVIDENCE = {"read": (), "extracted": (), "surfaced": (), "searched": ()}

# These exact field orders are the independently frozen lease's public records.
SCHEMA_FIELDS = {
    "WorkflowState": "phase module_id step_id ticket_id attempt prior_period_id current_period_id outcome",
    "OwnerClose": "schema_version outcome owner_receipt_sha256 owner_snapshot_sha256",
    "ReviewOutcome": "schema_version module_id step_id ticket_id attempt disposition issue_count error_codes snapshot_sha256 next_phase stored_payload_sha256",
    "OwnerBinding": "run_id issuer_id as_of method_version pack_sha256 snapshot_sha256 module_id step_id ticket_id attempt inputs",
    "FactReference": "producer_module_id producer_sha256 fact_id table_id row_id field",
    "CitationHandle": "source_id source_sha256 locator",
    "OperandReference": "fact period_id basis_id source_period source_basis fact_sha256 citation_handles",
    "OperandLineage": "measure_id prior current companions",
    "MeasureSelection": "measure_id prior_fact_id current_fact_id companion_fact_ids",
    "EarningsDeltaReview": "schema_version prior_period_id current_period_id selections comparison_assessment driver_assessment guidance_assessment",
    "EarningsPointRecord": "measure_id prior_fact_id current_fact_id companion_fact_ids prior_value current_value prior_status current_status delta delta_status delta_unit growth growth_status reason unit currency scale",
    "EarningsReportRecord": "producer_sha256 prior_period_id current_period_id prior_basis_id current_basis_id points limitations",
    "OwnerToolReceipt": "schema_version call_id sequence binding tool arguments status body error_code source_evidence",
    "OwnerSession": "session_id index binding normalized_grant_json access_manifest_json",
    "OwnerAccessRead": "schema_version session_id sequence binding access_manifest_json",
    "OwnerToolCall": "schema_version ordinal session_id receipt",
    "EarningsParticipation": "schema_version binding session_id grant_sha256 manifest_sha256 access_read_sha256 call_ids successful_call_ids manifest_call_ids period_lookup_call_ids metric_lookup_call_ids citation_call_ids",
    "OwnerSubmissionEnvelope": "schema_version binding raw_review_sha256 review participation",
    "EarningsOwnerStage": "schema_version review_sha256 participation_sha256 report operands candidate",
    "BoundSubmission": "schema_version binding raw_payload_sha256 stored_payload_sha256 canonical_review_sha256 call_ids successful_call_ids source_evidence input_read_hashes participation_sha256 owner_session_id normalization_paths prefilled_paths prefilled_kinds",
    "SubmissionIntent": "index binding snapshot_before_sha256",
    "SubmissionOutcome": "intent_sha256 disposition issues snapshot_after_sha256 step_sha256 step_output_sha256 candidate_sha256 result_sha256",
    "BeginRecord": "index module_id snapshot_before_sha256 snapshot_after_sha256 ticket_id attempt error_code",
    "OwnerHeadRecord": "ticket_id attempt head candidate_sha256 step_sha256s",
    "SourceIdentity": "source_id status sha256",
    "OwnerPins": "case_manifest_sha256 source_manifest_sha256 core_expected_sha256 access_expected_sha256 render_expected_sha256 owner_expected_sha256 sources",
    "OwnerSetup": "schema_version run pack_sha256 initial_snapshot_sha256 case_id pins participant transport policy_sha256",
    "TransportMessage": "index operation request_sha256",
    "AuditEntry": "kind sha256",
    "EarningsOwnerReceipt": "schema_version run pack_sha256 owner_snapshot_sha256 case_id pins participant transport outcome cp0 cp1 cp1b cp1b_stage_sha256 transport_messages begins foundation_calls foundation_input_reads owner_sessions owner_access_reads owner_calls submission_intents submission_outcomes audit_inventory publication_files",
}
SCHEMA_VERSIONS = {
    "OwnerClose": "cp1b-owner-close/1",
    "ReviewOutcome": "cp1b-review-outcome/1",
    "EarningsDeltaReview": "cp1b-review/1",
    "OwnerToolReceipt": "tool-receipt/1",
    "OwnerAccessRead": "cp1b-access-read/1",
    "OwnerToolCall": "cp1b-owner-call/1",
    "EarningsParticipation": "cp1b-participation/1",
    "OwnerSubmissionEnvelope": "cp1b-owner-submission/1",
    "EarningsOwnerStage": "cp1b-owner-stage/1",
    "BoundSubmission": "cp1b-bound-submission/1",
    "EarningsOwnerReceipt": "cp1b-owner-receipt/1",
    "OwnerSetup": "cp1b-owner-setup/1",
}
ERROR_CODES = (
    "bad_arguments",
    "not_permitted",
    "stale_binding",
    "identity_mismatch",
    "participation_incomplete",
    "transport_limit",
    "validation_failed",
    "internal_error",
)


def api():
    # Import only inside tests, so the pre-implementation RED is a named feature
    # assertion rather than an unrelated collection/import failure.
    assert importlib.util.find_spec("deploy_workflow.earnings_workflow") is not None, (
        "B1 earnings owner workflow is not implemented"
    )
    return importlib.import_module("deploy_workflow.earnings_workflow")


def pack_for(case_id):
    """Literal sources and new descriptor Run; no financial engine or old run."""
    from deploy_vii.contracts import Run, Source, Span
    from deploy_vii.preparation import PreparedPack

    case = next(c for c in DESCRIPTOR["cases"] if c["case_id"] == case_id)
    sources = []
    for source in SOURCE["sources"]:
        missing = case["source_state"] == "financial_missing" and source["source_id"] == "financial"
        sources.append(
            Source(
                source_id=source["source_id"],
                name=source["name"],
                media_type=None,
                status="missing" if missing else "ready",
                sha256=None if missing else source["sha256"],
                spans=() if missing else tuple(Span(**p) for p in source["pages"]),
                coverage=(),
                extractor="supplied-representation",
                extraction_status="blocked" if missing else "complete",
                limitation="Quarterly financial statements were not supplied."
                if missing
                else "Unaudited without auditor; borrower, guarantor and restricted perimeters unavailable."
                if source["source_id"] == "financial"
                else None,
            )
        )
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(case["run"])), sources=tuple(sources)
    )


def binding_data():
    return {
        "run_id": "slice-cp1b-flat-v1",
        "issuer_id": "northbridge-synthetic",
        "as_of": "2026-01-10",
        "method_version": "deploy-v-r14",
        "pack_sha256": "a" * 64,
        "snapshot_sha256": "b" * 64,
        "module_id": "CP-1B",
        "step_id": "earnings_delta",
        "ticket_id": "ticket.owner",
        "attempt": 0,
        "inputs": (),
    }


def review_data():
    # Artificial IDs test only the actor schema, never authentic participation.
    return {
        "prior_period_id": "q3-2025",
        "current_period_id": "q4-2025",
        "selections": tuple(
            {
                "measure_id": m,
                "prior_fact_id": f"prior.{m}",
                "current_fact_id": f"current.{m}",
                "companion_fact_ids": (f"metric.{m}",),
            }
            for m in MEASURES
        ),
        "comparison_assessment": "flat_sequential",
        "driver_assessment": "not_supplied",
        "guidance_assessment": "not_supplied",
    }


def point_data():
    return {
        "measure_id": "revenue",
        "prior_fact_id": "prior.revenue",
        "current_fact_id": "current.revenue",
        "companion_fact_ids": ("metric.revenue",),
        "prior_value": Decimal("30.00"),
        "current_value": Decimal("30.0"),
        "prior_status": "known",
        "current_status": "known",
        "delta": Decimal("0.00"),
        "delta_status": "known",
        "delta_unit": "MILLIONS",
        "growth": Decimal("0.0"),
        "growth_status": "known",
        "reason": None,
        "unit": "MILLIONS",
        "currency": "USD",
        "scale": Decimal(1000000),
    }


def test_public_api():
    core = api()
    expected = {
        "create": ("directory", "pack", "case_manifest", "case_id", "participant", "transport"),
        "open": ("directory", "case_manifest", "participant", "transport"),
        "state": ("self",),
        "invoke": ("self", "tool_name", "arguments"),
        "read_inputs": ("self",),
        "submit_review": ("self", "payload"),
        "write_receipt": ("self", "destination"),
    }
    for name, parameters in expected.items():
        assert (
            tuple(inspect.signature(getattr(core.EarningsWorkflow, name)).parameters) == parameters
        )
    create = inspect.signature(core.EarningsWorkflow.create).parameters
    assert (
        create["participant"].default == "trusted-python"
        and create["transport"].default == "python-api"
    )
    for name in ("case_manifest", "case_id", "participant", "transport"):
        assert create[name].kind == inspect.Parameter.KEYWORD_ONLY
    assert tuple(inspect.signature(core.submit_earnings_delta).parameters) == (
        "store",
        "ticket_id",
        "payload",
    )
    assert tuple(inspect.signature(core.verify_earnings_owner_receipt).parameters) == (
        "store",
        "receipt",
    )
    # The stream's encoding/raw-byte behavior is intentionally not asserted yet.
    assert callable(core.serve_json_lines)
    assert issubclass(core.OwnerError, ValueError)


def test_public_enum_aliases():
    core = api()
    assert get_args(core.OwnerCaseId) == ("E-QOQ-FLAT", "E-NO-YOY", "E-REQUIRED-CP1-MISSING")
    assert get_args(core.Transport) == ("python-api", "bounded-json-lines/1")
    assert get_args(core.Phase) == (
        "source_readiness",
        "source_context",
        "financials",
        "narrative",
        "readiness",
        "quality",
        "earnings_delta",
        "complete",
        "failed",
    )
    assert get_args(core.OutcomeKind) == ("owner_settled", "cp1_not_authorized")


@pytest.mark.parametrize("name", SCHEMA_FIELDS)
def test_frozen_schema_exact_order_required_fields_and_defaults(name):
    core = api()
    from deploy_vii.contracts import Contract

    record = getattr(core, name)
    assert issubclass(record, Contract)
    assert tuple(record.model_fields) == tuple(SCHEMA_FIELDS[name].split())
    assert record.model_config["frozen"] is True
    assert record.model_config["strict"] is True
    assert record.model_config["extra"] == "forbid"
    assert record.model_config["allow_inf_nan"] is False
    for field, definition in record.model_fields.items():
        if field == "schema_version":
            assert definition.default == SCHEMA_VERSIONS[name]
        else:
            assert definition.is_required(), (name, field)


@pytest.mark.parametrize("code", ERROR_CODES)
def test_owner_error_exposes_frozen_category(code):
    core = api()
    error = core.OwnerError(code)
    assert error.code == code


def test_actor_review_schema_has_twelve_selections_and_no_financial_answers():
    core = api()
    value = core.EarningsDeltaReview.model_validate(review_data())
    assert tuple(s.measure_id for s in value.selections) == MEASURES
    assert tuple(value.model_dump()) == tuple(ORACLE["review"]["fields"])
    assert tuple(value.selections[0].model_dump()) == tuple(ORACLE["review"]["selection_fields"])
    with pytest.raises(ValidationError):
        value.driver_assessment = "asserted management explanation"
    for count in (0, 11, 13):
        invalid = review_data()
        invalid["selections"] = (invalid["selections"] * 2)[:count]
        with pytest.raises(ValidationError):
            core.EarningsDeltaReview.model_validate(invalid)


@pytest.mark.parametrize("field", (*ORACLE["review"]["forbidden_fields"], "owner_session_id"))
def test_actor_review_rejects_extra_numeric_status_hash_quote_and_module_fields(field):
    core = api()
    invalid = {**review_data(), field: "must never become an actor-supplied answer"}
    with pytest.raises(ValidationError):
        core.EarningsDeltaReview.model_validate(invalid)


def test_lineage_records_cannot_embed_numeric_answers_or_raw_quotes():
    core = api()
    reference = {
        "producer_module_id": "CP-1",
        "producer_sha256": "c" * 64,
        "fact_id": "source.revenue",
        "table_id": "T4.10",
        "row_id": "metric.revenue",
        "field": "model-basis:" + "d" * 64,
    }
    handle = {
        "source_id": "financial",
        "source_sha256": ORACLE["pins"]["financial_source_sha256"],
        "locator": "page:2",
    }
    operand = {
        "fact": reference,
        "period_id": "q4-2025",
        "basis_id": "model-basis:" + "d" * 64,
        "source_period": "Q4 25: 2025-10-01 to 2025-12-31",
        "source_basis": "IFRS · consolidated group",
        "fact_sha256": "e" * 64,
        "citation_handles": (handle, handle),
    }
    value = core.OperandReference.model_validate(operand)
    assert len(value.citation_handles) == 2
    assert value.citation_handles[0] == value.citation_handles[1]
    assert tuple(value.model_dump()) == tuple(ORACLE["lineage"]["operand_reference_fields"])
    for extra in ("amount", "quote", "citations"):
        with pytest.raises(ValidationError):
            core.OperandReference.model_validate({**operand, extra: "not a reference"})
    with pytest.raises(ValidationError):
        core.CitationHandle.model_validate({**handle, "quote": "private source quote"})


def test_point_record_is_frozen_finite_and_preserves_decimal_quantum():
    core = api()
    record = core.EarningsPointRecord.model_validate(point_data())
    assert record.prior_value.as_tuple() == Decimal("30.00").as_tuple()
    assert record.current_value.as_tuple() == Decimal("30.0").as_tuple()
    with pytest.raises(ValidationError):
        record.current_value = Decimal(99)
    for number in ("NaN", "sNaN", "Infinity", "-Infinity"):
        with pytest.raises(ValidationError):
            core.EarningsPointRecord.model_validate(
                {**point_data(), "current_value": Decimal(number)}
            )


@pytest.mark.parametrize("field,value", [("attempt", True), ("attempt", -1), ("attempt", 2)])
def test_owner_binding_rejects_bool_or_out_of_range_attempt(field, value):
    core = api()
    with pytest.raises(ValidationError):
        core.OwnerBinding.model_validate({**binding_data(), field: value})


@pytest.mark.parametrize("field,value", [("sequence", True), ("sequence", 0), ("sequence", -1)])
def test_owner_tool_receipt_requires_positive_nonbool_sequence(field, value):
    core = api()
    payload = {
        "call_id": "call.owner",
        "sequence": 1,
        "binding": binding_data(),
        "tool": "read_access_projection",
        "arguments": {},
        "status": "refused",
        "body": None,
        "error_code": "bad_arguments",
        "source_evidence": EMPTY_EVIDENCE,
    }
    with pytest.raises(ValidationError):
        core.OwnerToolReceipt.model_validate({**payload, field: value})


@pytest.mark.parametrize("evidence_field", ("read", "extracted", "surfaced", "searched"))
def test_owner_receipt_cannot_claim_source_read_credit(evidence_field):
    core = api()
    evidence = {
        **EMPTY_EVIDENCE,
        evidence_field: ("revenue",)
        if evidence_field == "searched"
        else (("financial", "page:2"),),
    }
    payload = {
        "call_id": "call.owner",
        "sequence": 1,
        "binding": binding_data(),
        "tool": "read_access_projection",
        "arguments": {},
        "status": "refused",
        "body": None,
        "error_code": "bad_arguments",
        "source_evidence": evidence,
    }
    with pytest.raises(ValidationError):
        core.OwnerToolReceipt.model_validate(payload)


@pytest.mark.parametrize("case_id", tuple(c["case_id"] for c in DESCRIPTOR["cases"]))
def test_source_only_pack_fixture_uses_exact_new_run_and_literal_source_shape(case_id):
    api()
    pack = pack_for(case_id)
    case = next(c for c in ORACLE["manifest"]["cases"] if c["case_id"] == case_id)
    assert pack.run.model_dump(mode="json") == {"schema_version": "run/2", **case["run"]}
    assert tuple(pack.run.requested_modules) == ("CP-1B", "CP-5")
    assert tuple(s.source_id for s in pack.sources) == ("identity", "financial")
    for source, original in zip(pack.sources, SOURCE["sources"], strict=True):
        assert (
            source.name == original["name"] and source.coverage == () and source.media_type is None
        )
        assert source.extractor == "supplied-representation"
        if case["source_state"] == "financial_missing" and source.source_id == "financial":
            assert source.status == "missing" and source.sha256 is None and source.spans == ()
            assert (
                source.extraction_status == "blocked"
                and source.limitation == "Quarterly financial statements were not supplied."
            )
        else:
            assert tuple(s.model_dump() for s in source.spans) == tuple(
                {
                    "formula": None,
                    "cached_value": None,
                    "hidden": False,
                    "data_type": None,
                    "number_format": None,
                    "note": None,
                    **p,
                }
                for p in original["pages"]
            )
            assert source.status == "ready" and source.extraction_status == "complete"
            assert (
                hashlib.sha256("\f".join(s.text for s in source.spans).encode()).hexdigest()
                == original["sha256"]
                == source.sha256
            )


@pytest.mark.parametrize("case_id", tuple(c["case_id"] for c in DESCRIPTOR["cases"]))
def test_factory_begins_only_fresh_cp0_without_publication(tmp_path, case_id):
    core = api()
    from deploy_vii.execution import Execution

    pack = pack_for(case_id)
    directory = tmp_path / "owner"
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id=case_id
    )
    state = workflow.state()
    case = next(c for c in DESCRIPTOR["cases"] if c["case_id"] == case_id)
    assert (
        state.phase == "source_readiness"
        and state.module_id == "CP-0"
        and state.step_id == "source_readiness"
    )
    assert state.ticket_id is not None and state.attempt == 0 and state.outcome is None
    assert (state.prior_period_id, state.current_period_id) == (
        case["prior_period_id"],
        case["current_period_id"],
    )
    snapshot = Execution(directory).read()
    assert snapshot.run == pack.run and snapshot.pack_sha256 == pack.content_hash()
    assert snapshot.heads == ()
    assert len(snapshot.attempts) == 1
    assert (
        snapshot.attempts[0].module_id,
        snapshot.attempts[0].status,
        snapshot.attempts[0].ticket_id,
    ) == ("CP-0", "pending", state.ticket_id)
    assert not tuple(directory.rglob("model.html")) and not tuple(
        directory.rglob("calculation.json")
    )
    assert not (directory / "earnings-owner-audit/owner-receipt.json").exists()


def test_fresh_factory_rejects_input_read_and_premature_close_without_settlement(tmp_path):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    workflow = core.EarningsWorkflow.create(
        directory, pack_for("E-QOQ-FLAT"), case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    before = Execution(directory).read().content_hash()
    for operation in (
        workflow.read_inputs,
        lambda: workflow.write_receipt(tmp_path / "owner-receipt.json"),
    ):
        with pytest.raises(core.OwnerError) as error:
            operation()
        assert error.value.code == "not_permitted"
        assert Execution(directory).read().content_hash() == before
    assert not (tmp_path / "owner-receipt.json").exists()


@pytest.mark.parametrize(
    "updates", [{"participant": ""}, {"transport": "unbounded"}, {"case_id": "E-FOREIGN"}]
)
def test_factory_rejects_unsupported_setup_before_creating_store(tmp_path, updates):
    core = api()
    options = {"case_manifest": CASE_MANIFEST, "case_id": "E-QOQ-FLAT"}
    directory = tmp_path / "owner"
    with pytest.raises(core.OwnerError) as error:
        core.EarningsWorkflow.create(directory, pack_for("E-QOQ-FLAT"), **{**options, **updates})
    assert error.value.code in {"bad_arguments", "identity_mismatch"}
    assert not directory.exists()


def test_factory_rejects_old_run_and_tampered_source_bytes_without_mutating_input(tmp_path):
    core = api()
    pack = pack_for("E-QOQ-FLAT")
    original = pack.model_dump_json()
    wrong_run = pack.model_copy(
        update={"run": pack.run.model_copy(update={"run_id": "old-credit-snapshot"})}
    )
    source = pack.sources[1]
    wrong_source = source.model_copy(
        update={
            "spans": (
                source.spans[0].model_copy(update={"text": source.spans[0].text + " changed"}),
                *source.spans[1:],
            )
        }
    )
    wrong_bytes = pack.model_copy(update={"sources": (pack.sources[0], wrong_source)})
    for index, invalid in enumerate((wrong_run, wrong_bytes)):
        directory = tmp_path / f"owner-{index}"
        with pytest.raises(core.OwnerError) as error:
            core.EarningsWorkflow.create(
                directory, invalid, case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
            )
        assert error.value.code == "identity_mismatch" and not directory.exists()
    assert pack.model_dump_json() == original


def test_open_source_epoch_binds_participant_and_transport_without_an_extra_begin(tmp_path):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    workflow = core.EarningsWorkflow.create(
        directory,
        pack_for("E-QOQ-FLAT"),
        case_manifest=CASE_MANIFEST,
        case_id="E-QOQ-FLAT",
        participant="source-participant",
        transport="python-api",
    )
    before = Execution(directory).read().content_hash()
    reopened = core.EarningsWorkflow.open(
        directory,
        case_manifest=CASE_MANIFEST,
        participant="source-participant",
        transport="python-api",
    )
    assert (
        reopened.state() == workflow.state()
        and Execution(directory).read().content_hash() == before
    )
    for participant, transport in (
        ("foreign-participant", "python-api"),
        ("source-participant", "bounded-json-lines/1"),
    ):
        with pytest.raises(core.OwnerError) as error:
            core.EarningsWorkflow.open(
                directory, case_manifest=CASE_MANIFEST, participant=participant, transport=transport
            )
        assert error.value.code == "identity_mismatch"
        assert Execution(directory).read().content_hash() == before


def test_reopen_replays_real_source_calls_preserving_actual_receipt_ids_in_bound_submission(
    tmp_path,
):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    workflow = core.EarningsWorkflow.create(
        directory, pack_for("E-QOQ-FLAT"), case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    receipt = workflow.invoke(
        "read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1}
    )
    assert receipt["status"] == "ok"
    before = Execution(directory).read()
    reopened = core.EarningsWorkflow.open(
        directory, case_manifest=CASE_MANIFEST, participant="trusted-python", transport="python-api"
    )
    outcome = reopened.submit_review("{}")
    assert outcome.disposition == "refused" and outcome.error_codes == ("participation_incomplete",)
    intents = audit_records(core, directory, "intents", core.SubmissionIntent)
    assert len(intents) == 1
    assert (
        intents[0].binding.call_ids
        == intents[0].binding.successful_call_ids
        == (receipt["call_id"],)
    )
    assert intents[0].binding.owner_session_id is None
    assert Execution(directory).read() == before


def audit_records(core, directory, kind, model):
    folder = directory / "earnings-owner-audit" / kind
    records = (
        tuple(model.model_validate_json(p.read_bytes()) for p in folder.iterdir())
        if folder.exists()
        else ()
    )
    return records


def transport_input(chunks):
    return b"".join(
        bytes.fromhex(c["hex"]) if "hex" in c else bytes.fromhex(c["repeat_hex"]) * c["count"]
        for c in chunks
    )


def binary_workflow(core, directory):
    return core.EarningsWorkflow.create(
        directory,
        pack_for("E-QOQ-FLAT"),
        case_manifest=CASE_MANIFEST,
        case_id="E-QOQ-FLAT",
        participant="bounded-component",
        transport="bounded-json-lines/1",
    )


def test_unique_setup_is_durable_before_first_actual_begin(tmp_path, monkeypatch):
    core = api()
    from deploy_vii.execution import Execution

    original = Execution.begin
    observed = []

    def checked_begin(store, module_id):
        setup = audit_records(core, store.directory, "setup", core.OwnerSetup)
        assert len(setup) == 1
        initial = store.read()
        assert initial.parent is None and initial.attempts == initial.heads == ()
        assert setup[0].initial_snapshot_sha256 == initial.content_hash()
        assert (
            setup[0].policy_sha256
            == "7fba44bc1cf2d2dd8b26ed941c28b04371ce29f1875f070f48dc6d12b7efa8d6"
        )
        observed.append(module_id)
        return original(store, module_id)

    monkeypatch.setattr(Execution, "begin", checked_begin)
    workflow = binary_workflow(core, tmp_path / "owner")
    assert observed == ["CP-0"] and workflow.state().phase == "source_readiness"
    setup = audit_records(core, tmp_path / "owner", "setup", core.OwnerSetup)[0]
    path = tmp_path / "owner/earnings-owner-audit/setup" / setup.content_hash()
    assert path.read_bytes() == setup.model_dump_json().encode()
    assert tuple(setup.model_dump()) == tuple(TRANSPORT_ORACLE["owner_setup"]["ordered_fields"])


@pytest.mark.parametrize("failure_kind", ["setup", "begins", "begin_before_write"])
def test_bootstrap_interruption_preserves_exact_authority_and_narrow_recovery(
    tmp_path, monkeypatch, failure_kind
):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    original_retain, original_begin = core._retain, Execution.begin

    def failed_retain(store, kind, record):
        if kind == failure_kind:
            raise OSError("injected durable write failure")
        return original_retain(store, kind, record)

    def failed_begin(store, module_id):
        raise OSError("interrupted before actual begin")

    monkeypatch.setattr(core, "_retain", failed_retain)
    if failure_kind == "begin_before_write":
        monkeypatch.setattr(Execution, "begin", failed_begin)
    with pytest.raises(OSError):
        binary_workflow(core, directory)
    before = Execution(directory).read()
    monkeypatch.setattr(core, "_retain", original_retain)
    monkeypatch.setattr(Execution, "begin", original_begin)
    if failure_kind == "setup":
        assert before.attempts == ()
        with pytest.raises(core.OwnerError) as error:
            core.EarningsWorkflow.open(
                directory,
                case_manifest=CASE_MANIFEST,
                participant="bounded-component",
                transport="bounded-json-lines/1",
            )
        assert error.value.code == "identity_mismatch" and Execution(directory).read() == before
    else:
        reopened = core.EarningsWorkflow.open(
            directory,
            case_manifest=CASE_MANIFEST,
            participant="bounded-component",
            transport="bounded-json-lines/1",
        )
        after = Execution(directory).read()
        assert (
            len(after.attempts) == 1 and reopened.state().ticket_id == after.attempts[0].ticket_id
        )
        if failure_kind == "begins":
            assert after == before  # Actual ticket is recovered; begin is not repeated.
        assert len(audit_records(core, directory, "begins", core.BeginRecord)) == 1
        assert not audit_records(core, directory, "foundation-calls", core.FinancialCall)


@pytest.mark.parametrize("mutation", ["extra", "noncanonical", "wrong_policy", "missing"])
def test_open_refuses_setup_tamper_without_journal_mutation(tmp_path, mutation):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    binary_workflow(core, directory)
    before = Execution(directory).read()
    folder = directory / "earnings-owner-audit/setup"
    path = next(folder.iterdir())
    if mutation == "extra":
        (folder / ("f" * 64)).write_bytes(path.read_bytes())
    elif mutation == "noncanonical":
        path.write_text(json.dumps(json.loads(path.read_bytes()), indent=2))
    elif mutation == "wrong_policy":
        setup = core.OwnerSetup.model_validate_json(path.read_bytes()).model_copy(
            update={"policy_sha256": "0" * 64}
        )
        path.unlink()
        (folder / setup.content_hash()).write_bytes(setup.model_dump_json().encode())
    else:
        path.unlink()
    with pytest.raises(core.OwnerError) as error:
        core.EarningsWorkflow.open(
            directory,
            case_manifest=CASE_MANIFEST,
            participant="bounded-component",
            transport="bounded-json-lines/1",
        )
    assert error.value.code == "identity_mismatch" and Execution(directory).read() == before


@pytest.mark.parametrize("case", TRANSPORT_ORACLE["fixtures"], ids=lambda c: c["case_id"])
def test_raw_transport_captures_exact_independent_frame_and_does_not_drain(tmp_path, case):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    workflow = binary_workflow(core, directory)
    before = Execution(directory).read()
    raw = transport_input(case["input_chunks"])
    source, sink = io.BytesIO(raw), io.BytesIO()
    reader = io.TextIOWrapper(source, encoding="ascii", errors="ignore", newline=None)
    writer = io.TextIOWrapper(sink, encoding="ascii", errors="strict", newline="\r\n")
    try:
        core.serve_json_lines(workflow, reader, writer, destination=tmp_path / "receipt.json")
        messages = sorted(
            audit_records(core, directory, "transport-messages", core.TransportMessage),
            key=lambda m: m.index,
        )
        expected = case["expected"]
        assert len(messages) == expected["transport_message_count"]
        if messages:
            message = messages[0]
            captured = (
                directory / "earnings-owner-audit/payloads" / message.request_sha256
            ).read_bytes()
            assert message.operation == expected["operation"]
            assert len(captured) == case["first_read"]["length"]
            assert (
                hashlib.sha256(captured).hexdigest()
                == case["first_read"]["sha256"]
                == message.request_sha256
            )
            assert source.tell() == case["first_read"]["length"]
            unread = source.read()
            assert len(unread) == case["remaining_unread"]["length"]
            assert hashlib.sha256(unread).hexdigest() == case["remaining_unread"]["sha256"]
            replies = [json.loads(line) for line in sink.getvalue().splitlines()]
            assert len(replies) == 1
            if expected["error_code"] is not None:
                assert replies[0] == {"status": "refused", "error_code": expected["error_code"]}
            else:
                assert replies[0]["status"] == "ok" and set(replies[0]) == {"status", "result"}
        else:
            assert sink.getvalue() == b"" and source.tell() == 0
        if not expected["dispatch_allowed"] or expected["operation"] == "state":
            assert Execution(directory).read() == before
        assert not (directory / "earnings-owner-audit/owner-receipt.sha256").exists()
        assert not (tmp_path / "receipt.json").exists()
    finally:
        reader.detach()
        writer.detach()


@pytest.mark.parametrize("case", TRANSPORT_ORACLE["sequences"], ids=lambda c: c["case_id"])
def test_complete_invalid_frame_can_be_followed_by_separately_retained_control(tmp_path, case):
    core = api()
    directory = tmp_path / "owner"
    workflow = binary_workflow(core, directory)
    source, sink = io.BytesIO(transport_input(case["input_chunks"])), io.BytesIO()
    reader, writer = io.TextIOWrapper(source), io.TextIOWrapper(sink)
    try:
        core.serve_json_lines(workflow, reader, writer, destination=tmp_path / "receipt.json")
        messages = sorted(
            audit_records(core, directory, "transport-messages", core.TransportMessage),
            key=lambda m: m.index,
        )
        assert len(messages) == case["messages"] == 2
        for message, expected in zip(messages, case["frames"], strict=True):
            captured = (
                directory / "earnings-owner-audit/payloads" / message.request_sha256
            ).read_bytes()
            assert message.operation == expected["operation"]
            assert len(captured) == expected["bytes"]["length"]
            assert message.request_sha256 == expected["bytes"]["sha256"]
        replies = [json.loads(line) for line in sink.getvalue().splitlines()]
        assert replies[0] == {"status": "refused", "error_code": "bad_arguments"}
        assert replies[1]["status"] == "ok"
    finally:
        reader.detach()
        writer.detach()


def test_stringio_transport_setup_refuses_before_consumption_or_new_audit(tmp_path):
    core = api()
    directory = tmp_path / "owner"
    workflow = binary_workflow(core, directory)
    reader, writer = io.StringIO('{"op":"state"}\n'), io.StringIO()
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    with pytest.raises(core.OwnerError) as error:
        core.serve_json_lines(workflow, reader, writer, destination=tmp_path / "receipt.json")
    assert error.value.code == "bad_arguments" and reader.tell() == 0 and writer.getvalue() == ""
    assert before == {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }


def test_binary_reply_encoder_bypasses_text_encoding_and_newline_translation():
    core = api()
    sink = io.BytesIO()
    writer = io.TextIOWrapper(sink, encoding="ascii", newline="\r\n")
    expected = TRANSPORT_ORACLE["output"]["unicode_encoder_fixture"]
    try:
        core._write_reply(writer, expected["value"])
        assert sink.getvalue() == bytes.fromhex(expected["exact_hex"])
        assert hashlib.sha256(sink.getvalue()).hexdigest() == expected["sha256"]
    finally:
        writer.detach()


@pytest.mark.parametrize("failure_kind", ["payloads", "transport-messages"])
def test_transport_retention_failure_never_dispatches_or_erases_observed_bytes(
    tmp_path, monkeypatch, failure_kind
):
    core = api()
    directory = tmp_path / "owner"
    workflow = binary_workflow(core, directory)
    original_payload, original_retain = core._payload, core._retain

    def fail_payload(store, raw):
        raise OSError("injected raw retention failure")

    def fail_metadata(store, kind, record):
        if kind == "transport-messages":
            raise OSError("injected metadata retention failure")
        return original_retain(store, kind, record)

    if failure_kind == "payloads":
        monkeypatch.setattr(core, "_payload", fail_payload)
    else:
        monkeypatch.setattr(core, "_retain", fail_metadata)
    raw = b'{"op":"state"}\n'
    source, sink = io.BytesIO(raw), io.BytesIO()
    reader, writer = io.TextIOWrapper(source), io.TextIOWrapper(sink)
    try:
        with pytest.raises(OSError):
            core.serve_json_lines(workflow, reader, writer, destination=tmp_path / "receipt.json")
        assert sink.getvalue() == b""
        assert not audit_records(core, directory, "transport-messages", core.TransportMessage)
        retained = directory / "earnings-owner-audit/payloads" / hashlib.sha256(raw).hexdigest()
        assert retained.exists() is (failure_kind == "transport-messages")
    finally:
        reader.detach()
        writer.detach()
        monkeypatch.setattr(core, "_payload", original_payload)


def test_bound_submission_session_field_order_nullness_and_no_legacy_default():
    core = api()
    payload = {
        "binding": binding_data(),
        "raw_payload_sha256": "a" * 64,
        "stored_payload_sha256": "a" * 64,
        "canonical_review_sha256": None,
        "call_ids": (),
        "successful_call_ids": (),
        "source_evidence": EMPTY_EVIDENCE,
        "input_read_hashes": (),
        "participation_sha256": None,
        "owner_session_id": "actual-session-reference-required",
        "normalization_paths": (),
        "prefilled_paths": (),
        "prefilled_kinds": (),
    }
    record = core.BoundSubmission.model_validate(payload)
    assert tuple(record.model_dump()) == tuple(SESSION_ORACLE["schema_change"]["field_order"])
    assert record.owner_session_id == payload["owner_session_id"]
    for mutation in ({"owner_session_id": None}, {"owner_session_id": 1}):
        with pytest.raises(ValidationError):
            core.BoundSubmission.model_validate({**payload, **mutation})
    del payload["owner_session_id"]
    with pytest.raises(ValidationError):
        core.BoundSubmission.model_validate(payload)


def test_owner_read_hash_domain_includes_session_even_with_equal_binding_and_header():
    core = api()
    # Schema/hash-domain component only: these are not real settled sessions.
    common = {"sequence": 1, "binding": binding_data(), "access_manifest_json": '{"same":"header"}'}
    first = core.OwnerAccessRead.model_validate({**common, "session_id": "component-session-one"})
    second = core.OwnerAccessRead.model_validate({**common, "session_id": "component-session-two"})
    assert (
        first.binding == second.binding
        and first.access_manifest_json == second.access_manifest_json
    )
    assert first.content_hash() != second.content_hash()
    assert first.content_hash() != hashlib.sha256(first.access_manifest_json.encode()).hexdigest()


def test_absent_active_owner_session_refuses_before_a_qualified_binding_is_written(tmp_path):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    binary_workflow(core, directory)
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    with pytest.raises(core.OwnerError) as error:
        core._prepare_bound(
            Execution(directory), core.OwnerBinding.model_validate(binding_data()), "{}", None
        )
    assert error.value.code == "not_permitted"
    assert before == {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }


def projection_rows(body, prefix):
    """Read actual authorized table rows; never synthesize a financial answer."""
    columns = None
    result = []
    for line in body.splitlines():
        if line.startswith(prefix + ":") and " columns=" in line:
            columns = json.loads(line.split(" columns=", 1)[1])
        elif columns is not None and line.startswith("["):
            result.append(dict(zip(columns, json.loads(line), strict=True)))
        elif columns is not None:
            break
    return result


def foundation_review(pack, missing=False):
    # Reuse independently authored literal judgments, not its factory or old Run.
    from test_financial_workflow import readiness

    review = json.loads(readiness(pack, gap=missing))
    template = review["consumers"][0]
    review["consumers"] = [
        {**template, "module_id": module} for module in ("CP-1", "CP-1B", "CP-5")
    ]
    for gap in review["gaps"]:
        gap["affected_modules"] = ["CP-1", "CP-1B", "CP-5"]
    review["objective"] = (
        "Reported earnings comparison within the supplied source and scope limitations"
    )
    return json.dumps(review)


def downstream_review(read):
    from test_financial_workflow import parsed_evidence

    rows = parsed_evidence(read.body)
    requests = projection_rows(read.body, "consumers")
    assert tuple(r["entry"] for r in requests) == ("CP-1B", "CP-5")
    expected_requirements = {
        "CP-1B": ("normalized_financials", "entity_scope"),
        "CP-5": ("structured_data",),
    }
    statements = tuple(
        next(r["evidence_id"] for r in rows if r["kind"] == kind and r["amount"] is not None)
        for kind in ("statement_IS", "statement_CFS", "statement_BS")
    )
    entity = next(r["evidence_id"] for r in rows if r["kind"] == "entity")
    gap_ids = tuple(
        dict.fromkeys(
            [r["gap_id"] for r in rows if r["kind"] == "gap"]
            + [r["gap_id"] for r in projection_rows(read.body, "narrative_gaps")]
        )
    )
    rationale = "Located consolidated source supports this bounded use, with the retained source and perimeter limits."
    consumers = []
    for request in requests:
        assert tuple(request["requirements"]) == expected_requirements[request["entry"]]
        requirements = [
            {
                "requirement": key,
                "status": "limited",
                "evidence_ids": [entity] if key == "entity_scope" else list(statements),
                "rationale": rationale,
                "actions": [
                    "Obtain audited statements and missing creditor perimeter evidence before stronger use."
                ],
            }
            for key in request["requirements"]
        ]
        gaps = [
            {
                "gap_ids": [gap_id],
                "relevance": "relevant",
                "evidence_ids": [],
                "rationale": "Retain this actual upstream limitation in the selected earnings and integrity scope.",
            }
            for gap_id in gap_ids
        ]
        consumers.append({"entry": request["entry"], "requirements": requirements, "gaps": gaps})
    return json.dumps({"consumers": consumers})


def drive_fresh_foundation(core, directory, case_id="E-QOQ-FLAT"):
    from test_financial_workflow import context, financials, narrative, parsed_evidence

    pack = pack_for(case_id)
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id=case_id
    )
    missing = case_id == "E-REQUIRED-CP1-MISSING"
    for source in ("identity", "financial"):
        call = workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
        assert call["status"] == ("refused" if missing and source == "financial" else "ok")
        if missing and source == "financial":
            assert call["error_code"] == "unavailable" and call["body"] is None
    outcome = workflow.submit_review(foundation_review(pack, missing))
    assert outcome.disposition == "valid", outcome
    if missing:
        assert (
            workflow.state().phase == "complete"
            and workflow.state().outcome == "cp1_not_authorized"
        )
        return workflow
    assert workflow.state().phase == "source_context"
    for source in ("identity", "financial"):
        assert (
            workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})[
                "status"
            ]
            == "ok"
        )
    assert (
        workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})["status"]
        == "ok"
    )
    assert workflow.submit_review(context(pack)).disposition == "valid"
    assert workflow.state().phase == "financials"
    assert (
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 5})[
            "status"
        ]
        == "ok"
    )
    assert (
        workflow.invoke(
            "extract_statements",
            {"source_id": "financial", "locators": ["page:2", "page:3", "page:4"]},
        )["status"]
        == "ok"
    )
    assert (
        workflow.invoke("search_pack", {"query": "not disclosed", "source_id": "financial"})[
            "status"
        ]
        == "ok"
    )
    assert workflow.submit_review(json.dumps(financials(pack))).disposition == "valid"
    narrative_read = workflow.read_inputs()
    assert isinstance(narrative_read, core.InputRead)
    observed = parsed_evidence(narrative_read.body)
    assert (
        workflow.submit_review(
            json.dumps(narrative(narrative_read.model_dump(mode="json")))
        ).disposition
        == "valid"
    )
    readiness_read = workflow.read_inputs()
    assert workflow.submit_review(downstream_review(readiness_read)).disposition == "valid"
    quality_read = workflow.read_inputs()
    inputs = json.loads(quality_read.body)
    calculated_ids = {r["evidence_id"] for r in observed if r["kind"] == "kpi"}
    observed_ids = {r["evidence_id"] for r in observed}
    assert all(set(claim["evidence_ids"]) <= observed_ids for claim in inputs["claims"])
    # Authored source/lineage judgments only; Python calculates the actual QA.
    qa = {
        "claims": [
            {
                "claim_id": claim["claim_id"],
                "material": True,
                "evidence": [
                    {
                        "evidence_id": eid,
                        "lineage_class": "Calculated"
                        if eid in calculated_ids
                        else "Directly Sourced",
                        "rationale": "Actual Python KPI calculation"
                        if eid in calculated_ids
                        else "Actual located source or entity observation",
                    }
                    for eid in claim["evidence_ids"]
                ],
                "rationale": "Material bounded historical credit consideration",
            }
            for claim in inputs["claims"]
        ]
    }
    outcome = workflow.submit_review(json.dumps(qa))
    assert outcome.disposition == "valid", outcome
    assert workflow.state().phase == "earnings_delta"
    return workflow


def read_owner_scope(
    core, workflow, *, manifest=True, projection=True, citations=True, bootstrap=True
):
    if bootstrap:
        access = workflow.read_inputs()
        assert isinstance(access, core.OwnerAccessRead)
        header = json.loads(access.access_manifest_json)
    else:
        # This branch is for an intentionally incomplete component only. Trusted
        # setup metadata does not count as an actual actor bootstrap read.
        header = json.loads(workflow._owner_session.access_manifest_json)
    collected, projected, ids = [], [], []
    for tool, enabled, destination in (
        ("read_access_manifest", manifest, collected),
        ("read_access_projection", projection, projected),
    ):
        if not enabled:
            continue
        cursor = None
        while True:
            call = workflow.invoke(
                tool,
                {
                    "producer_module_id": "CP-1",
                    "producer_sha256": header["producer"]["sha256"],
                    "manifest_sha256": header["manifest_sha256"],
                    "cursor": cursor,
                    "limit": 20,
                },
            )
            assert call["status"] == "ok", call
            assert call["source_evidence"] == {k: [] for k in EMPTY_EVIDENCE}
            body = call["body"]
            assert len(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()) <= 8192
            assert body["offset"] == len(destination)
            destination.extend(body["entries"])
            ids.append(call["call_id"])
            cursor = body["next_cursor"]
            if body["complete"]:
                assert cursor is None
                break
    if projected:
        assert len(projected) == header["coordinate_count"]
        assert all(set(entry) == set(ORACLE["grant"]["projected_fields"]) for entry in projected)
        assert all(
            "quote" not in handle for entry in projected for handle in entry["citation_handles"]
        )
    if collected and projected:
        assert [(e["fact_id"], e["table_id"], e["row_id"], e["field"]) for e in collected] == [
            (e["fact_id"], e["table_id"], e["row_id"], e["field"]) for e in projected
        ]
    if citations:
        assert collected or projected
        fact_ids = [e["fact_id"] for e in (collected or projected)]
        for start in range(0, len(fact_ids), 20):
            call = workflow.invoke(
                "verify_upstream",
                {
                    "producer_module_id": "CP-1",
                    "producer_sha256": header["producer"]["sha256"],
                    "kind": "citations",
                    "fact_ids": fact_ids[start : start + 20],
                },
            )
            assert call["status"] == "ok" and call["body"]["verdict"] == "valid"
            ids.append(call["call_id"])
    return header, projected, ids


def owner_review(workflow, projected):
    periods, metrics = {}, {}
    for entry in projected:
        target = periods if entry["table_id"] == "T4.14" else metrics
        target.setdefault(entry["row_id"], {})[entry["field"]] = entry
    periods_by_id = {row["period_id"]["text"]: row for row in periods.values()}
    prior, current = workflow.state().prior_period_id, workflow.state().current_period_id

    def basis(pid):
        kind = "Q" if periods_by_id[pid]["period_type"]["text"] == "QUARTER" else "FY"
        parts = ("historical", f"{kind}:{pid}")
        return (
            "model-basis:"
            + hashlib.sha256("".join(f"{len(p)}:{p}" for p in parts).encode()).hexdigest()
        )

    current_basis = basis(current)
    prior_basis = basis(prior) if prior in periods_by_id else None
    metric_rows = {row["field_1"]["text"]: row for row in metrics.values()}
    period_fields = (
        "period_id",
        "period_type",
        "fiscal_year",
        "fiscal_quarter",
        "start_date",
        "end_date",
        "currency",
        "unit",
        "accounting_basis",
        "entity_perimeter",
    )
    selections = []
    for measure in MEASURES:
        row = metric_rows[measure]
        companions = [
            row["field_1"]["fact_id"],
            *(
                periods_by_id[pid][field]["fact_id"]
                for pid in (prior, current)
                if pid in periods_by_id
                for field in period_fields
            ),
        ]
        selections.append(
            {
                "measure_id": measure,
                "prior_fact_id": row[prior_basis]["fact_id"] if prior_basis else None,
                "current_fact_id": row[current_basis]["fact_id"],
                "companion_fact_ids": companions,
            }
        )
    return json.dumps(
        {
            "prior_period_id": prior,
            "current_period_id": current,
            "selections": selections,
            "comparison_assessment": "flat_sequential"
            if prior_basis
            else "comparative_not_supplied",
            "driver_assessment": "not_supplied",
            "guidance_assessment": "not_supplied",
        }
    )


@pytest.fixture(scope="module")
def real_owner_foundation(tmp_path_factory):
    core = api()
    directory = tmp_path_factory.mktemp("cp1b-source-foundation") / "owner"
    drive_fresh_foundation(core, directory)
    return directory


def reopen_component(core, foundation, destination):
    # Component recovery copies retain the same authentic Run/audit bytes. They
    # are not counted as another fresh source execution or issuer qualification.
    shutil.copytree(foundation, destination)
    return core.EarningsWorkflow.open(
        destination,
        case_manifest=CASE_MANIFEST,
        participant="trusted-python",
        transport="python-api",
    )


def test_real_fresh_foundation_runs_all_five_current_source_stages_without_model(
    real_owner_foundation,
):
    core = api()
    from deploy_vii.cp1_workflow import CP1_PROMOTION, PROMOTED
    from deploy_vii.execution import Execution

    store = Execution(real_owner_foundation)
    snapshot = store.read()
    assert snapshot.run.pathway == "earnings_update" and snapshot.run.requested_modules == (
        "CP-1B",
        "CP-5",
    )
    assert tuple(h.module_id for h in snapshot.heads) == ("CP-0", "CP-1")
    cp1 = next(a for a in snapshot.attempts if a.module_id == "CP-1")
    assert tuple(s.step_id for s in cp1.steps) == CP1_PROMOTION
    assert all(s.status == "valid" for s in cp1.steps)
    assert next(h for h in snapshot.heads if h.module_id == "CP-1").qualification == PROMOTED
    assert tuple(a.module_id for a in snapshot.attempts if a.status == "pending") == ("CP-1B",)
    calls = audit_records(core, real_owner_foundation, "foundation-calls", core.FinancialCall)
    assert {c.binding.step_id for c in calls} == {
        "source_readiness",
        "source_context",
        "financials",
    }
    assert len({c.binding.snapshot_sha256 for c in calls}) == 3
    bounds = audit_records(core, real_owner_foundation, "bindings", core.BoundSubmission)
    assert all(b.owner_session_id is None for b in bounds)
    assert any(b.prefilled_paths for b in bounds)
    assert not tuple(real_owner_foundation.rglob("model.html")) and not tuple(
        real_owner_foundation.rglob("calculation.json")
    )


@pytest.fixture(scope="module")
def complete_owner_scope(real_owner_foundation, tmp_path_factory):
    core = api()
    directory = tmp_path_factory.mktemp("cp1b-real-read-scope") / "owner"
    workflow = reopen_component(core, real_owner_foundation, directory)
    header, projected, _ = read_owner_scope(core, workflow)
    assert (
        header["coordinate_count"]
        == ORACLE["B1_transport_proof"]["cases"]["E-QOQ-FLAT"]["coordinates"]
    )
    return directory, owner_review(workflow, projected)


def test_actual_manifest_projection_and_citations_cover_all_granted_attributes(
    complete_owner_scope,
):
    core = api()
    directory, review = complete_owner_scope
    sessions = audit_records(core, directory, "owner-sessions", core.OwnerSession)
    selected = max(sessions, key=lambda s: s.index)
    calls = sorted(
        audit_records(core, directory, "owner-calls", core.OwnerToolCall), key=lambda c: c.ordinal
    )
    assert any(c.receipt.tool == "read_access_manifest" for c in calls)
    projection = [
        entry
        for c in calls
        if c.receipt.tool == "read_access_projection"
        for entry in c.receipt.body["entries"]
    ]
    assert len(projection) == 138 and {e["table_id"] for e in projection} == {"T4.14", "T4.10"}
    assert any(
        len(e["citation_handles"]) >= 2 and e["citation_handles"][0] == e["citation_handles"][1]
        for e in projection
    )
    reads = audit_records(core, directory, "owner-reads", core.OwnerAccessRead)
    assert len([r for r in reads if r.session_id == selected.session_id]) == 1
    actor = json.loads(review)
    assert tuple(s["measure_id"] for s in actor["selections"]) == MEASURES
    assert set(actor) == set(ORACLE["review"]["fields"]) - {"schema_version"}
    assert not any(key in actor for key in ORACLE["review"]["forbidden_fields"])


@pytest.mark.parametrize("omission", ["bootstrap", "manifest", "projection", "citations"])
def test_complete_permission_or_other_session_reads_cannot_replace_selected_participation(
    tmp_path, complete_owner_scope, omission
):
    core = api()
    from deploy_vii.execution import Execution

    template, raw_review = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    selected = workflow._owner_session
    before = Execution(directory).read()
    read_owner_scope(core, workflow, **{omission: False})
    result = workflow.submit_review(raw_review)
    assert result.disposition == "refused" and result.error_codes == ("participation_incomplete",)
    assert Execution(directory).read() == before
    intent = max(
        audit_records(core, directory, "intents", core.SubmissionIntent), key=lambda i: i.index
    )
    assert (
        intent.binding.owner_session_id == selected.session_id
        and intent.binding.participation_sha256 is None
    )
    assert intent.binding.stored_payload_sha256 == intent.binding.raw_payload_sha256
    assert not next(a for a in before.attempts if a.status == "pending").steps


def test_refused_empty_session_is_not_upgraded_by_earlier_or_later_complete_reads(
    tmp_path, complete_owner_scope
):
    core = api()
    from deploy_vii.execution import Execution

    template, raw_review = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    selected = workflow._owner_session
    before = Execution(directory).read()
    result = workflow.submit_review(raw_review)
    assert result.disposition == "refused" and result.error_codes == ("participation_incomplete",)
    first = max(
        audit_records(core, directory, "intents", core.SubmissionIntent), key=lambda i: i.index
    )
    assert first.binding.owner_session_id == selected.session_id
    old_reads = audit_records(core, directory, "owner-reads", core.OwnerAccessRead)
    assert first.binding.input_read_hashes and all(
        r.session_id != selected.session_id for r in old_reads
    )
    assert first.binding.input_read_hashes == tuple(r.content_hash() for r in old_reads)
    read_owner_scope(core, workflow)
    rebound, issues = core._prepare_bound_readonly(Execution(directory), first)
    assert rebound == first.binding and issues == ("participation_incomplete",)
    assert Execution(directory).read() == before
    later_reads = audit_records(core, directory, "owner-reads", core.OwnerAccessRead)
    selected_reads = [r for r in later_reads if r.session_id == selected.session_id]
    assert selected_reads and all(
        r.content_hash() not in first.binding.input_read_hashes for r in selected_reads
    )
    assert any(r.access_manifest_json == selected_reads[0].access_manifest_json for r in old_reads)


def test_malformed_actor_review_still_binds_current_actual_session_without_a_step(
    tmp_path, complete_owner_scope
):
    core = api()
    from deploy_vii.execution import Execution

    template, raw_review = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    before = Execution(directory).read()
    selected = workflow._owner_session
    raw = json.dumps({**json.loads(raw_review), "owner_session_id": "actor-cannot-select"})
    result = workflow.submit_review(raw)
    assert result.disposition == "refused" and result.error_codes == ("bad_arguments",)
    intent = max(
        audit_records(core, directory, "intents", core.SubmissionIntent), key=lambda i: i.index
    )
    assert intent.binding.owner_session_id == selected.session_id
    assert (
        intent.binding.canonical_review_sha256 is None
        and intent.binding.participation_sha256 is None
    )
    assert Execution(directory).read() == before


def test_unresolved_empty_session_intent_reopens_same_epoch_and_exact_raw_bytes_only(
    tmp_path, complete_owner_scope, monkeypatch
):
    core = api()
    from deploy_vii.execution import Execution

    template, raw_review = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    selected = workflow._owner_session
    before = Execution(directory).read()
    original = core._complete_intent

    def interrupted(store, intent):
        raise OSError("interrupted after durable intent and before outcome")

    monkeypatch.setattr(core, "_complete_intent", interrupted)
    with pytest.raises(OSError):
        workflow.submit_review(raw_review)
    monkeypatch.setattr(core, "_complete_intent", original)
    sessions_before = audit_records(core, directory, "owner-sessions", core.OwnerSession)
    reopened = core.EarningsWorkflow.open(
        directory, case_manifest=CASE_MANIFEST, participant="trusted-python", transport="python-api"
    )
    assert audit_records(core, directory, "owner-sessions", core.OwnerSession) == sessions_before
    assert reopened._owner_session.session_id == selected.session_id
    with pytest.raises(core.OwnerError) as wrong:
        reopened.submit_review(raw_review + " ")
    assert wrong.value.code == "identity_mismatch"
    with pytest.raises(core.OwnerError):
        reopened.read_inputs()
    result = reopened.submit_review(raw_review)
    assert result.disposition == "refused" and result.error_codes == ("participation_incomplete",)
    assert Execution(directory).read() == before
    # Recovery must restore a usable capability only AFTER resolving the frozen
    # old intent; a new actual epoch never changes that old captured prefix.
    next_access = reopened.read_inputs()
    assert isinstance(next_access, core.OwnerAccessRead)
    assert next_access.session_id != selected.session_id
    assert reopened._owner_session.index == selected.index + 1
    assert core._prepare_bound_readonly(
        Execution(directory),
        max(
            audit_records(core, directory, "intents", core.SubmissionIntent), key=lambda i: i.index
        ),
    )[1] == ("participation_incomplete",)
    again = core.EarningsWorkflow.open(
        directory, case_manifest=CASE_MANIFEST, participant="trusted-python", transport="python-api"
    )
    assert again._owner_session.session_id != selected.session_id
    assert again._owner_session.index == selected.index + 2


@pytest.mark.parametrize("mutation", ["unknown", "other_session", "body_digest", "future_read"])
def test_owner_session_or_typed_read_prefix_tamper_refuses_revalidation(
    tmp_path, complete_owner_scope, mutation
):
    core = api()
    from deploy_vii.execution import Execution

    template, raw_review = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    assert workflow.submit_review(raw_review).disposition == "refused"
    first = max(
        audit_records(core, directory, "intents", core.SubmissionIntent), key=lambda i: i.index
    )
    if mutation == "unknown":
        bound = first.binding.model_copy(update={"owner_session_id": "unknown-session"})
    elif mutation == "other_session":
        bound = first.binding.model_copy(
            update={
                "owner_session_id": min(
                    audit_records(core, directory, "owner-sessions", core.OwnerSession),
                    key=lambda s: s.index,
                ).session_id
            }
        )
    elif mutation == "body_digest":
        read = audit_records(core, directory, "owner-reads", core.OwnerAccessRead)[0]
        bound = first.binding.model_copy(
            update={
                "input_read_hashes": (
                    hashlib.sha256(read.access_manifest_json.encode()).hexdigest(),
                )
            }
        )
    else:
        read_owner_scope(core, workflow)
        latest = next(
            r
            for r in audit_records(core, directory, "owner-reads", core.OwnerAccessRead)
            if r.session_id == workflow._owner_session.session_id
        )
        bound = first.binding.model_copy(
            update={"input_read_hashes": (*first.binding.input_read_hashes, latest.content_hash())}
        )
    tampered = first.model_copy(update={"binding": bound})
    try:
        reconstructed, issues = core._prepare_bound_readonly(Execution(directory), tampered)
    except core.OwnerError:
        pass
    else:
        assert reconstructed != first.binding or issues != ("participation_incomplete",)


def test_owner_raw_source_tool_is_a_real_sanitized_refusal(tmp_path, complete_owner_scope):
    core = api()
    template, _ = complete_owner_scope
    workflow = reopen_component(core, template, tmp_path / "owner")
    receipt = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert (
        receipt["status"] == "refused"
        and receipt["error_code"] == "not_permitted"
        and receipt["body"] is None
    )
    assert receipt["source_evidence"] == {k: [] for k in EMPTY_EVIDENCE}
    assert '"quote"' not in json.dumps(receipt)


def settle_owner(core, workflow, destination):
    _, projected, _ = read_owner_scope(core, workflow)
    raw = owner_review(workflow, projected)
    outcome = workflow.submit_review(raw)
    assert outcome.disposition == "valid", outcome
    assert workflow.state().phase == "complete" and workflow.state().outcome == "owner_settled"
    receipt = workflow.write_receipt(destination)
    return receipt


@pytest.fixture(scope="module")
def settled_owner_component(complete_owner_scope, tmp_path_factory):
    core = api()
    template, _ = complete_owner_scope
    directory = tmp_path_factory.mktemp("cp1b-settled-component") / "owner"
    workflow = reopen_component(core, template, directory)
    receipt = settle_owner(core, workflow, directory.parent / "receipt.json")
    return directory, receipt


@pytest.mark.parametrize("case_id", ["E-QOQ-FLAT", "E-NO-YOY"])
def test_fresh_actual_owner_cases_settle_exact_values_lineage_claim_and_immutable_receipt(
    tmp_path, case_id
):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    workflow = drive_fresh_foundation(core, directory, case_id)
    receipt = settle_owner(core, workflow, tmp_path / "receipt.json")
    store = Execution(directory)
    snapshot = store.read()
    assert tuple(h.module_id for h in snapshot.heads) == ("CP-0", "CP-1", "CP-1B")
    assert not any(a.status == "pending" for a in snapshot.attempts)
    assert receipt.publication_files == receipt.transport_messages == ()
    assert (
        receipt.pins.owner_expected_sha256
        == "a37dc25f8f756364ae88726cdec3f2de1bbf4c20892ca910d22e9646186efd9d"
    )
    assert (
        (directory / "earnings-owner-audit/owner-receipt.json").read_bytes()
        == (tmp_path / "receipt.json").read_bytes()
        == receipt.model_dump_json().encode()
    )
    assert (
        directory / "earnings-owner-audit/owner-receipt.sha256"
    ).read_bytes() == receipt.content_hash().encode("ascii")
    assert len([e for e in receipt.audit_inventory if e.kind == "setup"]) == 1
    cp1 = store.head_module(next(h for h in snapshot.heads if h.module_id == "CP-1"))
    cp1b = store.head_module(next(h for h in snapshot.heads if h.module_id == "CP-1B"))
    stage = core.EarningsOwnerStage.model_validate_json(
        store.step_output(receipt.cp1b_stage_sha256)
    )
    assert len(cp1b.facts) == 44 and len(cp1b.claims) == 1 and len(stage.operands) == 12
    assert tuple(t.table_id for t in cp1b.tables) == ("T1B.1", "T1B.2", "T1B.3")
    assert tuple(o.measure_id for o in stage.operands) == MEASURES
    assert cp1b.status == "restricted" and receipt.cp1b.head.qualification is None
    assert stage.candidate.limitations == tuple(ORACLE["own_limitations"][case_id])
    assert cp1b.claims[0].text == ORACLE["claim"]["texts"][case_id]
    assert cp1b.claims[0].limitation == ORACLE["claim"]["limitations"][case_id]
    primary = {f.fact_id: f for f in cp1.facts}
    owned = {f.fact_id: f for f in cp1b.facts}
    for operand in stage.operands:
        for reference in (operand.prior, operand.current):
            if reference is None:
                continue
            fact = primary[reference.fact.fact_id]
            assert reference.fact.producer_sha256 == cp1.content_hash()
            assert reference.fact_sha256 == fact.content_hash()
            assert (reference.source_period, reference.source_basis) == (fact.period, fact.basis)
            assert tuple(h.model_dump() for h in reference.citation_handles) == tuple(
                {"source_id": c.source_id, "source_sha256": c.source_sha256, "locator": c.locator}
                for c in fact.citations
            )
        assert all(ref.fact_id in primary for ref in operand.companions)
    case = RENDER_ORACLE["positive" if case_id == "E-QOQ-FLAT" else "gap"]
    for table in case["tables"]:
        for row in table["rows"]:
            for expected in row["cells"]:
                fact = owned[expected["fact_id"]]
                assert fact.amount == (
                    None if expected["value"] is None else Decimal(expected["value"])
                )
                assert (fact.status, fact.unit, fact.currency, fact.scale, fact.period) == (
                    expected["status"],
                    expected["unit"],
                    expected["currency"],
                    Decimal(expected["scale"]),
                    expected["period"],
                )
    if case_id == "E-QOQ-FLAT":
        for point, expected in zip(
            stage.report.points, CORE_ORACLE["positive"]["points"], strict=True
        ):
            assert point.delta == (
                None if expected["delta"] is None else Decimal(expected["delta"])
            )
            assert point.growth_status == expected["growth_status"]
        assert all(p.prior is not None for p in stage.operands)
        assert (
            stage.report.points[-1].prior_status == "missing"
            and stage.report.points[-1].current_status == "known"
        )
    else:
        assert stage.report.prior_basis_id is None and all(o.prior is None for o in stage.operands)
        assert all(p.prior_value is p.delta is None for p in stage.report.points)
        assert owned["cp1b:T1B.2:cash_closing:current"].amount == Decimal(20)
        assert not owned["cp1b:T1B.1:revenue:prior"].citations
        assert any(f.text == "opening-2024" for f in cp1.facts if f.table_id == "T4.14")
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    assert core.verify_earnings_owner_receipt(store, receipt) is None
    assert before == {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }
    with pytest.raises(core.OwnerError):
        workflow.read_inputs()


def test_negative_fresh_source_case_records_actual_refusal_and_cp0_only_owner_boundary(tmp_path):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    workflow = drive_fresh_foundation(core, directory, "E-REQUIRED-CP1-MISSING")
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    snapshot = Execution(directory).read()
    assert (
        receipt.outcome == "cp1_not_authorized"
        and receipt.cp1 is receipt.cp1b is receipt.cp1b_stage_sha256 is None
    )
    assert tuple(h.module_id for h in snapshot.heads) == ("CP-0",)
    assert all(a.module_id == "CP-0" for a in snapshot.attempts)
    assert receipt.owner_sessions == receipt.owner_access_reads == receipt.owner_calls == ()
    assert any(
        b.module_id == "CP-1" and b.error_code == "not_authorized" and b.ticket_id is None
        for b in receipt.begins
    )
    assert any(
        c.tool == "read_pages"
        and c.arguments["source_id"] == "financial"
        and c.status == "refused"
        and c.body is None
        for c in receipt.foundation_calls
    )
    assert core.verify_earnings_owner_receipt(Execution(directory), receipt) is None


def test_actual_composed_new_money_figures_pass_and_old_numeric_chips_fail_existing_guard(
    settled_owner_component,
):
    core = api()
    from deploy_vii.execution import Execution, candidate_issues
    from deploy_vii.prose import prose_issues

    directory, receipt = settled_owner_component
    store = Execution(directory)
    snapshot = store.read()
    stage = core.EarningsOwnerStage.model_validate_json(
        store.step_output(receipt.cp1b_stage_sha256)
    )
    attempt = next(a for a in snapshot.attempts if a.ticket_id == receipt.cp1b.ticket_id)
    assert prose_issues(stage.candidate, names=(snapshot.run.issuer_name,)) == ()
    assert candidate_issues(snapshot, attempt, stage.candidate, pack=store.pack()) == ()
    import re

    old_text = re.sub(r"\{([^|{}]+)\|MILLIONS\}", r"[\1]", stage.candidate.claims[0].text)
    bad = stage.candidate.model_copy(
        update={"claims": (stage.candidate.claims[0].model_copy(update={"text": old_text}),)}
    )
    assert prose_issues(bad, names=(snapshot.run.issuer_name,))
    assert candidate_issues(snapshot, attempt, bad, pack=store.pack())


@pytest.mark.parametrize("defect", ["missing", "corrupt"])
def test_known_core_blob_integrity_failures_map_identity_and_never_recreate_bytes(
    tmp_path, settled_owner_component, defect
):
    core = api()
    from deploy_vii.execution import Execution

    template, receipt = settled_owner_component
    directory = tmp_path / "owner"
    shutil.copytree(template, directory)
    blob = directory / "blobs" / receipt.pack_sha256
    if defect == "missing":
        blob.unlink()
    else:
        blob.write_bytes(b"tampered pack bytes")
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    with pytest.raises(core.OwnerError) as error:
        core.verify_earnings_owner_receipt(Execution(directory), receipt)
    assert error.value.code == "identity_mismatch"
    assert before == {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }


def test_unexpected_verifier_programming_failure_still_propagates(
    settled_owner_component, monkeypatch
):
    core = api()
    from deploy_vii.execution import Execution

    directory, receipt = settled_owner_component

    def unexpected(*args, **kwargs):
        raise ValueError("unexpected programming sentinel")

    monkeypatch.setattr(core, "_snapshot", unexpected)
    with pytest.raises(ValueError, match="^unexpected programming sentinel$"):
        core.verify_earnings_owner_receipt(Execution(directory), receipt)


def cp5_review_payload(store, attempt):
    from deploy_vii.cp5_integrity import citation_ref, review_scope
    from deploy_vii.prose import tokenize

    scope = review_scope(store, attempt)
    assert not scope.issues
    assert {head.module_id for head in scope.evaluated} == {"CP-1", "CP-1B"}
    reviews = []
    for head in scope.evaluated:
        for claim in head.claims:
            refs = tuple(
                dict.fromkeys(run.text for run in tokenize(claim.text) if run.kind != "text")
            )
            refs = refs or tuple(
                citation_ref(claim.claim_id, n) for n in range(1, len(claim.citations) + 1)
            )
            reviews.append(
                {
                    "producer_module": head.module_id,
                    "claim_ref": claim.claim_id,
                    "support": "partly_supported" if refs else "unsupported",
                    "upstream_refs": refs,
                    "rationale": "Retained financial source and scope limitations keep this review bounded.",
                }
            )
    gap = {
        "gap": "Management guidance and causal driver evidence remain unavailable.",
        "why_it_matters": "The numerical comparison supports no stronger management inference.",
        "affected_modules": ["CP-1B"],
        "severity": "Material",
        "action": "Obtain current management disclosures before broader use.",
    }
    return json.dumps({"claim_reviews": reviews, "contradictions": [], "gaps": [gap]})


def test_real_refused_session_then_same_session_completion_settles_without_retroactive_credit(
    tmp_path, complete_owner_scope
):
    core = api()
    from deploy_vii.execution import Execution

    template, raw_review = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    selected = workflow._owner_session
    anchor = Execution(directory).read()
    first = workflow.submit_review(raw_review)
    assert first.disposition == "refused" and first.error_codes == ("participation_incomplete",)
    old_intent = max(
        audit_records(core, directory, "intents", core.SubmissionIntent), key=lambda i: i.index
    )
    assert old_intent.binding.owner_session_id == selected.session_id
    assert old_intent.binding.participation_sha256 is None
    read_owner_scope(core, workflow)
    assert workflow._owner_session == selected
    second = workflow.submit_review(raw_review)
    assert second.disposition == "valid" and workflow.state().outcome == "owner_settled"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    owner_intents = [
        i for i in receipt.submission_intents if isinstance(i.binding.binding, core.OwnerBinding)
    ]
    assert len(owner_intents) == 2
    first_intent, second_intent = owner_intents
    assert first_intent == old_intent
    assert (
        first_intent.binding.owner_session_id
        == second_intent.binding.owner_session_id
        == selected.session_id
    )
    assert first_intent.binding.input_read_hashes != second_intent.binding.input_read_hashes
    assert (
        first_intent.binding.call_ids
        == second_intent.binding.call_ids[: len(first_intent.binding.call_ids)]
    )
    earlier = next(
        o for o in receipt.submission_outcomes if o.intent_sha256 == first_intent.content_hash()
    )
    assert (
        earlier.disposition == "refused" and earlier.snapshot_after_sha256 == anchor.content_hash()
    )
    assert earlier.step_sha256 is earlier.candidate_sha256 is earlier.result_sha256 is None
    rebound, issues = core._prepare_bound_readonly(Execution(directory), first_intent)
    assert rebound == first_intent.binding and issues == ("participation_incomplete",)
    core.verify_earnings_owner_receipt(Execution(directory), receipt)


@pytest.mark.parametrize("failure_kind", ["factory", "persistence"])
def test_actual_owner_session_setup_failure_never_creates_a_null_or_future_binding(
    tmp_path, real_owner_foundation, monkeypatch, failure_kind
):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    shutil.copytree(real_owner_foundation, directory)
    before = Execution(directory).read()
    original_sessions = audit_records(core, directory, "owner-sessions", core.OwnerSession)
    original_retain = core._retain

    def failed_factory(*args, **kwargs):
        raise OSError("actual owner session factory interruption")

    def failed_retain(store, kind, value):
        if kind == "owner-sessions":
            raise OSError("actual owner session persistence interruption")
        return original_retain(store, kind, value)

    with monkeypatch.context() as patch:
        if failure_kind == "factory":
            patch.setattr(core.UpstreamTools, "from_execution", failed_factory)
        else:
            patch.setattr(core, "_retain", failed_retain)
        with pytest.raises(OSError):
            core.EarningsWorkflow.open(
                directory,
                case_manifest=CASE_MANIFEST,
                participant="trusted-python",
                transport="python-api",
            )
    assert Execution(directory).read() == before
    assert audit_records(core, directory, "owner-sessions", core.OwnerSession) == original_sessions
    assert all(
        not isinstance(i.binding.binding, core.OwnerBinding)
        for i in audit_records(core, directory, "intents", core.SubmissionIntent)
    )
    recovered = core.EarningsWorkflow.open(
        directory, case_manifest=CASE_MANIFEST, participant="trusted-python", transport="python-api"
    )
    assert recovered._owner_session.index == max(s.index for s in original_sessions) + 1
    assert isinstance(recovered.read_inputs(), core.OwnerAccessRead)


@pytest.mark.parametrize(
    "interrupt_at", ["pending_validation", "after_valid_step", "after_settlement"]
)
def test_real_retained_owner_submission_resumes_exact_session_and_finishes_once(
    tmp_path, complete_owner_scope, monkeypatch, interrupt_at
):
    core = api()
    from deploy_vii.execution import Execution

    template, _ = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    _, projection, _ = read_owner_scope(core, workflow)
    raw_review = owner_review(workflow, projection)
    selected = workflow._owner_session
    original_finish, original_retain = Execution.finish, core._retain

    def failed_validation(*args, **kwargs):
        raise RuntimeError("interrupted after retained step payload")

    def failed_finish(store, ticket_id, payload, validator, **kwargs):
        if isinstance(store, core._FrozenExecution):
            return original_finish(store, ticket_id, payload, validator, **kwargs)
        raise RuntimeError("interrupted after valid owner step")

    def failed_outcome(store, kind, value):
        if kind == "outcomes" and any(
            a.module_id == "CP-1B" and a.status == "finished" for a in store.read().attempts
        ):
            raise RuntimeError("interrupted after real owner settlement")
        return original_retain(store, kind, value)

    with monkeypatch.context() as patch:
        if interrupt_at == "pending_validation":
            patch.setattr(core, "_stage_validation", failed_validation)
        elif interrupt_at == "after_valid_step":
            patch.setattr(Execution, "finish", failed_finish)
        else:
            patch.setattr(core, "_retain", failed_outcome)
        with pytest.raises(RuntimeError):
            workflow.submit_review(raw_review)
    before_resume = Execution(directory).read()
    intent = max(
        audit_records(core, directory, "intents", core.SubmissionIntent), key=lambda i: i.index
    )
    assert intent.binding.owner_session_id == selected.session_id
    assert len([a for a in before_resume.attempts if a.module_id == "CP-1B"]) == 1
    sessions = audit_records(core, directory, "owner-sessions", core.OwnerSession)
    reopened = core.EarningsWorkflow.open(
        directory, case_manifest=CASE_MANIFEST, participant="trusted-python", transport="python-api"
    )
    assert audit_records(core, directory, "owner-sessions", core.OwnerSession) == sessions
    assert reopened._owner_session.session_id == selected.session_id
    with pytest.raises(core.OwnerError) as changed:
        reopened.submit_review(raw_review + " ")
    assert changed.value.code == "identity_mismatch"
    with pytest.raises(core.OwnerError):
        reopened.invoke("read_access_manifest", {})
    real_finishes = []

    def counted_finish(store, ticket_id, payload, validator, **kwargs):
        if not isinstance(store, core._FrozenExecution):
            real_finishes.append(ticket_id)
        return original_finish(store, ticket_id, payload, validator, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Execution, "finish", counted_finish)
        outcome = reopened.submit_review(raw_review)
    assert outcome.disposition == "valid" and reopened.state().outcome == "owner_settled"
    assert len(real_finishes) == (0 if interrupt_at == "after_settlement" else 1)
    receipt = reopened.write_receipt(tmp_path / "receipt.json")
    actual = Execution(directory).read()
    owner_attempts = [a for a in actual.attempts if a.module_id == "CP-1B"]
    assert len(owner_attempts) == 1 and len(owner_attempts[0].steps) == 1
    assert (
        len([o for o in receipt.submission_outcomes if o.intent_sha256 == intent.content_hash()])
        == 1
    )
    core.verify_earnings_owner_receipt(Execution(directory), receipt)


@pytest.mark.parametrize(
    "state",
    [
        "begin_pending",
        "retained_pending_step",
        "rejected_attempt_zero",
        "repair_begin_pending",
        "blocked_repair",
        "valid_settled",
        "valid_repair",
    ],
)
def test_owner_prefix_accepts_only_authentic_cp5_descendants_without_claiming_tool_acceptance(
    tmp_path, settled_owner_component, monkeypatch, state
):
    core = api()
    from deploy_vii import cp5_integrity
    from deploy_vii.cp1_workflow import PROMOTED
    from deploy_vii.execution import Execution

    template, receipt = settled_owner_component
    directory = tmp_path / "owner"
    shutil.copytree(template, directory)
    store = Execution(directory)
    owner_bytes = {
        p.relative_to(directory): p.read_bytes()
        for p in (directory / "earnings-owner-audit").rglob("*")
        if p.is_file()
    }
    attempt = store.begin("CP-5")
    if state in {"rejected_attempt_zero", "repair_begin_pending", "blocked_repair", "valid_repair"}:
        attempt = cp5_integrity.submit_cp5_step(store, attempt.ticket_id, "integrity_review", "{}")
        assert attempt.status == "finished" and attempt.issues
        if state != "rejected_attempt_zero":
            attempt = store.begin("CP-5")
            assert attempt.number == 1
        if state == "blocked_repair":
            attempt = cp5_integrity.submit_cp5_step(
                store, attempt.ticket_id, "integrity_review", "{}"
            )
            assert next(h for h in store.read().heads if h.module_id == "CP-5").status == "blocked"
    if state == "retained_pending_step":
        payload = cp5_review_payload(store, attempt)

        def interrupted(*args, **kwargs):
            raise RuntimeError("CP5 validation interrupted")

        with monkeypatch.context() as patch:
            patch.setattr(cp5_integrity, "validate_integrity", interrupted)
            with pytest.raises(RuntimeError):
                cp5_integrity.submit_cp5_step(store, attempt.ticket_id, "integrity_review", payload)
        assert (
            next(a for a in store.read().attempts if a.ticket_id == attempt.ticket_id)
            .steps[0]
            .status
            == "pending"
        )
    elif state in {"valid_settled", "valid_repair"}:
        payload = cp5_review_payload(store, attempt)
        attempt = cp5_integrity.submit_cp5_step(
            store, attempt.ticket_id, "integrity_review", payload
        )
        assert attempt.status == "finished" and not attempt.issues
        assert (
            next(h for h in store.read().heads if h.module_id == "CP-5").qualification == PROMOTED
        )
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    assert core.verify_earnings_owner_receipt(store, receipt) is None
    assert before == {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }
    assert owner_bytes == {
        p.relative_to(directory): p.read_bytes()
        for p in (directory / "earnings-owner-audit").rglob("*")
        if p.is_file()
    }
    assert receipt.owner_snapshot_sha256 != store.read().content_hash()
    # No CP5 tool receipt or A4/final-slice acceptance is asserted here.


@pytest.mark.parametrize("mutation", ["prefix_head_status", "prefix_attempt", "unselected_head"])
def test_owner_prefix_rejects_non_cp5_journal_mutations(
    tmp_path, settled_owner_component, mutation
):
    core = api()
    from deploy_vii.execution import Execution

    template, receipt = settled_owner_component
    directory = tmp_path / "owner"
    shutil.copytree(template, directory)
    store = Execution(directory)
    before = store.read()
    # Deliberate tamper fixtures only; these are never counted as actual heads.
    if mutation == "prefix_head_status":
        heads = tuple(
            h.model_copy(update={"status": "stale"}) if h.module_id == "CP-1" else h
            for h in before.heads
        )
        bad = before.model_copy(update={"parent": before.content_hash(), "heads": heads})
    elif mutation == "prefix_attempt":
        attempts = tuple(
            a.model_copy(update={"interruption": "tamper"}) if a.module_id == "CP-1" else a
            for a in before.attempts
        )
        bad = before.model_copy(update={"parent": before.content_hash(), "attempts": attempts})
    else:
        foreign = before.heads[-1].model_copy(update={"module_id": "CP-4"})
        bad = before.model_copy(
            update={"parent": before.content_hash(), "heads": (*before.heads, foreign)}
        )
    store._write(bad)
    with pytest.raises(core.OwnerError) as error:
        core.verify_earnings_owner_receipt(store, receipt)
    assert error.value.code == "identity_mismatch"


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_call",
        "extra_payload",
        "call_body",
        "missing_session",
        "duplicate_session_id",
        "pointer",
        "pointer_absent",
        "pointer_null",
        "grant",
        "header",
        "participation",
        "seal",
    ],
)
def test_actual_owner_audit_and_seal_tampering_never_qualifies_or_repairs_records(
    tmp_path, settled_owner_component, mutation
):
    core = api()
    from deploy_vii.execution import Execution

    template, receipt = settled_owner_component
    directory = tmp_path / "owner"
    shutil.copytree(template, directory)
    store = Execution(directory)
    owner_intent = next(
        i
        for i in reversed(receipt.submission_intents)
        if isinstance(i.binding.binding, core.OwnerBinding)
    )
    session = next(
        s for s in receipt.owner_sessions if s.session_id == owner_intent.binding.owner_session_id
    )
    if mutation == "missing_call":
        core._audit(store, "owner-calls", receipt.owner_calls[-1].content_hash()).unlink()
    elif mutation == "extra_payload":
        raw = b"unreferenced forensic payload"
        (directory / "earnings-owner-audit/payloads" / hashlib.sha256(raw).hexdigest()).write_bytes(
            raw
        )
    elif mutation == "call_body":
        call = receipt.owner_calls[-1]
        modified = call.model_copy(
            update={"receipt": call.receipt.model_copy(update={"body": {"invented": "value"}})}
        )
        core._audit(store, "owner-calls", call.content_hash()).write_bytes(
            modified.model_dump_json().encode()
        )
    elif mutation == "missing_session":
        core._audit(store, "owner-sessions", session.content_hash()).unlink()
    elif mutation == "duplicate_session_id":
        duplicate = session.model_copy(update={"index": session.index + 1})
        core._audit(store, "owner-sessions", duplicate.content_hash()).write_bytes(
            duplicate.model_dump_json().encode()
        )
        receipt = receipt.model_copy(
            update={"owner_sessions": (*receipt.owner_sessions, duplicate)}
        )
    elif mutation == "pointer":
        changed = owner_intent.model_copy(
            update={
                "binding": owner_intent.binding.model_copy(
                    update={"owner_session_id": "unrecognized-session"}
                )
            }
        )
        core._audit(store, "intents", owner_intent.content_hash()).write_bytes(
            changed.model_dump_json().encode()
        )
    elif mutation in {"pointer_absent", "pointer_null"}:
        data = owner_intent.model_dump(mode="json")
        if mutation == "pointer_absent":
            del data["binding"]["owner_session_id"]
        else:
            data["binding"]["owner_session_id"] = None
        core._audit(store, "intents", owner_intent.content_hash()).write_text(json.dumps(data))
    elif mutation in {"grant", "header"}:
        key = "normalized_grant_json" if mutation == "grant" else "access_manifest_json"
        data = json.loads(getattr(session, key))
        if mutation == "grant":
            data["producers"][0]["projected_fields"] = ["fact_id"]
        else:
            data["manifest_sha256"] = "f" * 64
        changed = session.model_copy(
            update={key: json.dumps(data, sort_keys=True, separators=(",", ":"))}
        )
        core._audit(store, "owner-sessions", session.content_hash()).write_bytes(
            changed.model_dump_json().encode()
        )
    elif mutation == "participation":
        part = core.EarningsParticipation.model_validate_json(
            core._audit(
                store, "participations", owner_intent.binding.participation_sha256
            ).read_bytes()
        )
        changed = part.model_copy(update={"session_id": "other-session"})
        core._audit(store, "participations", part.content_hash()).write_bytes(
            changed.model_dump_json().encode()
        )
    else:
        (directory / "earnings-owner-audit/owner-receipt.sha256").write_bytes(b"0" * 64)
    before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    with pytest.raises(core.OwnerError) as error:
        core.verify_earnings_owner_receipt(store, receipt)
    assert error.value.code == "identity_mismatch"
    assert before == {
        p.relative_to(directory): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }


def test_participation_pointer_cannot_name_another_actual_same_binding_session(
    settled_owner_component,
):
    core = api()
    from deploy_vii.execution import Execution

    directory, receipt = settled_owner_component
    intent = next(
        i
        for i in reversed(receipt.submission_intents)
        if isinstance(i.binding.binding, core.OwnerBinding)
    )
    selected = next(
        s for s in receipt.owner_sessions if s.session_id == intent.binding.owner_session_id
    )
    earlier = next(
        s
        for s in receipt.owner_sessions
        if s.binding == selected.binding and s.session_id != selected.session_id
    )
    assert earlier.access_manifest_json == selected.access_manifest_json
    altered = intent.model_copy(
        update={
            "binding": intent.binding.model_copy(update={"owner_session_id": earlier.session_id})
        }
    )
    with pytest.raises(core.OwnerError) as error:
        core._intent_session(Execution(directory), altered)
    assert error.value.code == "identity_mismatch"


def test_owner_receipt_strict_roundtrip_exposes_existing_public_import_boundary_only(
    settled_owner_component,
):
    core = api()
    from deploy_vii.execution import Execution

    directory, receipt = settled_owner_component
    parsed = core.EarningsOwnerReceipt.model_validate_json(receipt.model_dump_json())
    assert parsed == receipt
    assert all(
        i.binding.owner_session_id is not None
        for i in parsed.submission_intents
        if isinstance(i.binding.binding, core.OwnerBinding)
    )
    core.verify_earnings_owner_receipt(Execution(directory), parsed)
    # Actual A4 consumption/tool participation/final slice remains separately owned.


def test_foreign_session_cursors_and_extra_projection_filters_refuse_without_read_credit(
    tmp_path, complete_owner_scope
):
    core = api()
    template, raw_review = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    header = json.loads(workflow.read_inputs().access_manifest_json)
    previous_calls = audit_records(core, template, "owner-calls", core.OwnerToolCall)
    manifest_cursor = next(
        c.receipt.body["next_cursor"]
        for c in previous_calls
        if c.receipt.tool == "read_access_manifest" and c.receipt.body["next_cursor"] is not None
    )
    projection_cursor = next(
        c.receipt.body["next_cursor"]
        for c in previous_calls
        if c.receipt.tool == "read_access_projection" and c.receipt.body["next_cursor"] is not None
    )
    base = {
        "producer_module_id": "CP-1",
        "producer_sha256": header["producer"]["sha256"],
        "manifest_sha256": header["manifest_sha256"],
        "limit": 20,
    }
    for tool, cursor, expected in (
        ("read_access_manifest", manifest_cursor, "stale_binding"),
        ("read_access_projection", projection_cursor, "stale_binding"),
        ("read_access_projection", manifest_cursor, "stale_binding"),
        ("read_access_manifest", projection_cursor, "bad_arguments"),
    ):
        call = workflow.invoke(tool, {**base, "cursor": cursor})
        assert (
            call["status"] == "refused" and call["error_code"] == expected and call["body"] is None
        )
        assert call["source_evidence"] == {k: [] for k in EMPTY_EVIDENCE}
    call = workflow.invoke("read_access_projection", {**base, "cursor": None, "fields": ["amount"]})
    assert call["status"] == "refused" and call["error_code"] == "bad_arguments"
    result = workflow.submit_review(raw_review)
    assert result.disposition == "refused" and result.error_codes == ("participation_incomplete",)


@pytest.mark.parametrize(
    "defect", ["reordered", "duplicated", "same_period", "reverse_period", "wrong_fact"]
)
def test_well_shaped_wrong_owner_review_uses_actual_core_rejection_and_one_repair(
    tmp_path, complete_owner_scope, defect
):
    core = api()
    from deploy_vii.execution import Execution

    template, _ = complete_owner_scope
    directory = tmp_path / "owner"
    workflow = reopen_component(core, template, directory)
    _, entries, _ = read_owner_scope(core, workflow)
    review = json.loads(owner_review(workflow, entries))
    if defect == "reordered":
        review["selections"][0], review["selections"][1] = (
            review["selections"][1],
            review["selections"][0],
        )
    elif defect == "duplicated":
        review["selections"][1] = dict(review["selections"][0])
    elif defect == "same_period":
        review["prior_period_id"] = review["current_period_id"]
    elif defect == "reverse_period":
        review["prior_period_id"], review["current_period_id"] = (
            review["current_period_id"],
            review["prior_period_id"],
        )
    else:
        review["selections"][0]["current_fact_id"] = "nonexistent-fact"
    initial_ticket = workflow.state().ticket_id
    result = workflow.submit_review(json.dumps(review))
    assert result.disposition == "invalid" and result.error_codes == ("validation_failed",)
    snapshot = Execution(directory).read()
    rejected = next(a for a in snapshot.attempts if a.ticket_id == initial_ticket)
    assert rejected.status == "finished" and rejected.number == 0 and rejected.issues
    assert not any(h.module_id == "CP-1B" for h in snapshot.heads)
    assert Execution(directory).result(rejected.result_sha256).status == "rejected"
    pending = next(a for a in snapshot.attempts if a.status == "pending")
    assert (
        pending.module_id == "CP-1B" and pending.number == 1 and pending.repair_of == initial_ticket
    )
    assert not pending.steps
    assert workflow._owner_session.binding.ticket_id == pending.ticket_id
    if defect in {"same_period", "reverse_period"}:
        assert "incompatible_periods" in rejected.issues


def test_negative_owner_receipt_rejects_every_descendant_snapshot_mutation(tmp_path):
    core = api()
    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    workflow = drive_fresh_foundation(core, directory, "E-REQUIRED-CP1-MISSING")
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = Execution(directory)
    before = store.read()
    # Explicit malicious snapshot fixture, never accepted as an analytical head.
    fake = before.heads[0].model_copy(update={"module_id": "CP-1"})
    store._write(
        before.model_copy(update={"parent": before.content_hash(), "heads": (*before.heads, fake)})
    )
    with pytest.raises(core.OwnerError) as error:
        core.verify_earnings_owner_receipt(store, receipt)
    assert error.value.code == "identity_mismatch"


@pytest.mark.parametrize("failure", ["none", "short", "write", "flush", "read"])
def test_raw_binary_io_failures_remain_visible_with_exact_input_and_no_automatic_redispatch(
    tmp_path, failure
):
    core = api()

    class FaultyBuffer(io.BytesIO):
        enabled = False

        def readline(self, size=-1):
            if self.enabled and failure == "read":
                raise OSError("injected binary read failure")
            return super().readline(size)

        def write(self, raw):
            if self.enabled and failure == "none":
                return None
            if self.enabled and failure == "short":
                return super().write(raw[:-1])
            if self.enabled and failure == "write":
                raise OSError("injected binary write failure")
            return super().write(raw)

        def flush(self):
            if self.enabled and failure == "flush":
                raise OSError("injected binary flush failure")
            return super().flush()

    directory = tmp_path / "owner"
    workflow = binary_workflow(core, directory)
    raw = b'{"op":"submit_review","payload":"{}"}\n'
    source, sink = FaultyBuffer(raw), FaultyBuffer()
    reader, writer = io.TextIOWrapper(source), io.TextIOWrapper(sink)
    source.enabled = sink.enabled = True
    try:
        with pytest.raises(OSError):
            core.serve_json_lines(workflow, reader, writer, destination=tmp_path / "receipt.json")
        messages = audit_records(core, directory, "transport-messages", core.TransportMessage)
        if failure == "read":
            assert messages == ()
        else:
            assert (
                len(messages) == 1 and messages[0].request_sha256 == hashlib.sha256(raw).hexdigest()
            )
            intents = audit_records(core, directory, "intents", core.SubmissionIntent)
            outcomes = audit_records(core, directory, "outcomes", core.SubmissionOutcome)
            assert len(intents) == len(outcomes) == 1
        assert not (tmp_path / "receipt.json").exists()
    finally:
        source.enabled = sink.enabled = False
        reader.detach()
        writer.detach()


# ---------------------------------------------------------------------------
# Fix round 1: adversary findings H1-H3, M1, L1-L3 (see work/cp1b-owner-b1).
# ---------------------------------------------------------------------------


def nested_list(depth):
    value = 0
    for _ in range(depth):
        value = [value]
    return value


def read_foundation_sources(workflow):
    for source in ("identity", "financial"):
        call = workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
        assert call["status"] == "ok"


def cp1_attempts(workflow):
    return [a for a in workflow._store.read().attempts if a.module_id == "CP-1"]


def reopen_workflow(core, directory):
    return core.EarningsWorkflow.open(
        directory, case_manifest=CASE_MANIFEST, participant="trusted-python", transport="python-api"
    )


def cp0_to_source_context(core, directory):
    pack = pack_for("E-QOQ-FLAT")
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    read_foundation_sources(workflow)
    assert workflow.submit_review(foundation_review(pack)).disposition == "valid"
    assert workflow.state().phase == "source_context"
    return workflow


@pytest.mark.parametrize("second", ["{}", "{ }"])
def test_identical_invalid_cp1_resubmission_uses_the_repair_and_finishes_the_attempt(
    tmp_path, second
):
    core = api()
    directory = tmp_path / "owner"
    workflow = cp0_to_source_context(core, directory)
    read_foundation_sources(workflow)
    first = workflow.submit_review("{}")
    assert first.disposition == "invalid"
    (attempt,) = cp1_attempts(workflow)
    assert (attempt.status, len(attempt.step_repairs)) == ("pending", 1)
    read_foundation_sources(workflow)
    again = workflow.submit_review(second)
    # The second submission is a genuine second journal rejection: the single
    # repair is used up, the attempt is finished and attempt 1 is begun.
    assert again.disposition == "invalid"
    attempts = cp1_attempts(workflow)
    assert [(a.number, a.status) for a in attempts] == [(0, "finished"), (1, "pending")]
    assert workflow.state().attempt == 1
    reopened = reopen_workflow(core, directory)
    assert (reopened.state().phase, reopened.state().attempt) == ("source_context", 1)


def test_identical_invalid_cp1_bytes_without_a_new_read_refuse_and_leave_no_unresolved_intent(
    tmp_path,
):
    core = api()
    directory = tmp_path / "owner"
    workflow = cp0_to_source_context(core, directory)
    read_foundation_sources(workflow)
    assert workflow.submit_review("{}").disposition == "invalid"
    refused = workflow.submit_review("{}")
    assert refused.disposition == "refused"
    assert core._unresolved(workflow._store) == ()
    assert (
        workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})[
            "status"
        ]
        == "ok"
    )
    reopened = reopen_workflow(core, directory)
    assert reopened.state().phase == "source_context"


def test_deep_invoke_arguments_are_refused_before_a_session_sequence_is_consumed(tmp_path):
    core = api()
    directory = tmp_path / "owner"
    pack = pack_for("E-QOQ-FLAT")
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    with pytest.raises(core.OwnerError) as error:
        workflow.invoke(
            "read_pages",
            {"source_id": "identity", "first_page": 1, "last_page": 1, "x": nested_list(250)},
        )
    assert error.value.code == "bad_arguments"
    read_foundation_sources(workflow)
    calls = core._records(workflow._store, "foundation-calls", core.FinancialCall)
    assert sorted(c.sequence for c in calls) == [1, 2]
    assert workflow.submit_review(foundation_review(pack)).disposition == "valid"
    assert reopen_workflow(core, directory).state().phase == "source_context"


def test_deep_review_payload_is_refused_before_any_audit_write_and_the_run_still_seals(tmp_path):
    core = api()
    directory = tmp_path / "owner"
    pack = pack_for("E-REQUIRED-CP1-MISSING")
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id="E-REQUIRED-CP1-MISSING"
    )
    for source in ("identity", "financial"):
        workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
    payloads = directory / "earnings-owner-audit" / "payloads"
    before = sorted(p.name for p in payloads.iterdir()) if payloads.exists() else []
    with pytest.raises(core.OwnerError) as error:
        workflow.submit_review(json.dumps({"sources": nested_list(1000)}))
    assert error.value.code == "bad_arguments"
    assert (sorted(p.name for p in payloads.iterdir()) if payloads.exists() else []) == before
    assert core._records(workflow._store, "intents", core.SubmissionIntent) == ()
    assert workflow.submit_review(foundation_review(pack, True)).disposition == "valid"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert receipt.outcome == "cp1_not_authorized"


def test_put_crash_residue_in_an_audit_folder_does_not_brick_reopen(tmp_path):
    core = api()
    directory = tmp_path / "owner"
    pack = pack_for("E-QOQ-FLAT")
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
    residue = directory / "earnings-owner-audit" / "foundation-calls" / (".pending-" + "0" * 32)
    residue.write_bytes(b'{"partial"')
    reopened = reopen_workflow(core, directory)
    assert reopened.state().phase == "source_readiness"
    read = reopened.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert read["status"] == "ok" and read["sequence"] == 2


def test_positive_case_whose_cp0_blocks_cp1_fails_instead_of_taking_the_source_gap_outcome(
    tmp_path,
):
    core = api()
    directory = tmp_path / "owner"
    pack = pack_for("E-QOQ-FLAT")
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    read_foundation_sources(workflow)
    review = json.loads(foundation_review(pack))
    for consumer in review["consumers"]:
        if consumer["module_id"] == "CP-1":
            consumer["readiness"] = "BLOCKED"
    assert workflow.submit_review(json.dumps(review)).disposition == "valid"
    state = workflow.state()
    # LEAD ruling (B1 fix round 2, N3): in a positive case an actual CP-1 begin
    # denial ends in phase `failed`, not a sealable outcome. Lease :374-375 and
    # owner-expected.json `real_cp1_begin_denial` describe the negative case, where
    # `cp1_not_authorized` is the sealable genuine-negative outcome.
    assert (state.phase, state.outcome) == ("failed", None)
    with pytest.raises(core.OwnerError) as error:
        workflow.write_receipt(tmp_path / "receipt.json")
    assert error.value.code == "not_permitted"
    reopened = reopen_workflow(core, directory)
    assert (reopened.state().phase, reopened.state().outcome) == ("failed", None)


@pytest.mark.parametrize(
    "tamper", ["pointer_garbage", "pointer_non_ascii", "pointer_directory", "setup_directory"]
)
def test_core_and_audit_tamper_errors_map_to_identity_mismatch(tmp_path, tamper):
    core = api()
    from deploy_vii.execution import Execution

    base = tmp_path / "base" / "owner"
    workflow = drive_fresh_foundation(core, base, "E-REQUIRED-CP1-MISSING")
    receipt = workflow.write_receipt(tmp_path / "base" / "receipt.json")
    directory = tmp_path / "tampered"
    shutil.copytree(base, directory)
    if tamper == "pointer_garbage":
        (directory / "current").write_text("garbage\n")
    elif tamper == "pointer_non_ascii":
        (directory / "current").write_bytes("é\n".encode())
    elif tamper == "pointer_directory":
        (directory / "current").unlink()
        (directory / "current").mkdir()
    else:
        record = next((directory / "earnings-owner-audit" / "setup").iterdir())
        record.unlink()
        record.mkdir()
    with pytest.raises(core.OwnerError) as error:
        core.verify_earnings_owner_receipt(Execution(directory), receipt)
    assert error.value.code == "identity_mismatch"


def test_stage_validation_charges_only_the_actor_review_parse_to_the_actor(monkeypatch):
    core = api()
    from deploy_vii.contracts import Fact

    def composition_defect(*args, **kwargs):
        Fact.model_validate_json("{}")  # B1's own composition producing an invalid record

    monkeypatch.setattr(core, "_owner_stage", composition_defect)
    with pytest.raises(ValidationError):
        core._stage_validation(None, None)


def test_put_crash_residue_in_the_audit_root_does_not_block_the_seal(tmp_path):
    core = api()
    base = tmp_path / "owner"
    workflow = drive_fresh_foundation(core, base, "E-REQUIRED-CP1-MISSING")
    (base / "earnings-owner-audit" / (".pending-" + "1" * 32)).write_bytes(b'{"partial"')
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert receipt.outcome == "cp1_not_authorized"


def test_sealed_store_with_audit_root_residue_still_verifies_and_reopens(tmp_path):
    core = api()
    from deploy_vii.execution import Execution

    base = tmp_path / "owner"
    workflow = drive_fresh_foundation(core, base, "E-REQUIRED-CP1-MISSING")
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    (base / "earnings-owner-audit" / (".pending-" + "2" * 32)).write_bytes(b'{"partial"')
    core.verify_earnings_owner_receipt(Execution(base), receipt)
    reopened = reopen_workflow(core, base)
    assert (reopened.state().phase, reopened.state().outcome) == (
        "complete",
        "cp1_not_authorized",
    )


def test_tampered_stored_record_bytes_at_open_give_identity_mismatch(tmp_path):
    core = api()
    directory = tmp_path / "owner"
    cp0_to_source_context(core, directory)
    record = next((directory / "earnings-owner-audit" / "foundation-calls").iterdir())
    record.write_bytes(b"not json")
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, directory)
    assert error.value.code == "identity_mismatch"


@pytest.mark.parametrize("defect", [KeyError("missing"), RuntimeError("defect"), "validation"])
def test_programming_error_in_b1_composition_on_reopen_propagates_unchanged(
    tmp_path, monkeypatch, defect
):
    core = api()
    from deploy_vii.contracts import Fact

    directory = tmp_path / "owner"
    cp0_to_source_context(core, directory)

    def composition_defect(*args, **kwargs):
        if defect == "validation":
            Fact.model_validate_json("{}")  # B1's own composition producing an invalid record
        raise defect

    monkeypatch.setattr(core, "_propose_submission", composition_defect)
    expected = ValidationError if defect == "validation" else type(defect)
    with pytest.raises(expected) as error:
        reopen_workflow(core, directory)
    assert not isinstance(error.value, core.OwnerError)
    if defect != "validation":
        # The very defect object propagates: not re-raised, wrapped or mapped.
        assert error.value is defect


def test_integer_over_the_digit_limit_is_refused_as_bad_arguments_without_a_sequence(tmp_path):
    core = api()
    directory = tmp_path / "owner"
    pack = pack_for("E-QOQ-FLAT")
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    # Pin the interpreter's int/str digit limit the refusal depends on, so the test
    # does not change meaning under PYTHONINTMAXSTRDIGITS; restored afterwards.
    digit_limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    try:
        with pytest.raises(core.OwnerError) as error:
            workflow.invoke(
                "read_pages",
                {"source_id": "identity", "first_page": 1, "last_page": 1, "x": 10**4400},
            )
        assert error.value.code == "bad_arguments"
        read_foundation_sources(workflow)
        calls = core._records(workflow._store, "foundation-calls", core.FinancialCall)
        assert sorted(c.sequence for c in calls) == [1, 2]
        assert reopen_workflow(core, directory).state().phase == "source_readiness"
    finally:
        sys.set_int_max_str_digits(digit_limit)


# ---------------------------------------------------------------------------
# Fix round 3: adversary findings R1, L1, L2 (see work/cp1b-owner-b1).
# Tampered or deleted stored evidence at open(), write_receipt and the public
# verifier refuses identity_mismatch (lease: rejects deleted/tampered records;
# conflicting or ambiguous evidence refuses).
# ---------------------------------------------------------------------------

AUDIT = "earnings-owner-audit"
NOT_IN_CHAIN = "ab" * 32


def put_record(directory, kind, record):
    raw = record.model_dump_json().encode()
    folder = directory / AUDIT / kind
    folder.mkdir(parents=True, exist_ok=True)
    (folder / hashlib.sha256(raw).hexdigest()).write_bytes(raw)


def record_paths(directory, kind, model):
    folder = directory / AUDIT / kind
    return [(p, model.model_validate_json(p.read_bytes())) for p in sorted(folder.iterdir())]


def only_record(directory, kind, model):
    ((path, record),) = record_paths(directory, kind, model)
    return path, record


def current_snapshot(directory):
    from deploy_vii.execution import Execution

    return Execution(directory).read()


def forged_owner_binding(core, directory):
    current = current_snapshot(directory)
    return core.OwnerBinding(
        run_id=current.run.run_id,
        issuer_id=current.run.issuer_id,
        as_of=current.run.as_of.isoformat(),
        method_version=current.run.method_version,
        pack_sha256=current.pack_sha256,
        snapshot_sha256=NOT_IN_CHAIN,
        module_id="CP-1B",
        step_id="earnings_delta",
        ticket_id="forged-ticket",
        attempt=0,
        inputs=(),
    )


def lose_outcome_and_intent(core, directory):
    """The state after a crash between the journal mutation and the outcome write."""
    path, _ = only_record(directory, "outcomes", core.SubmissionOutcome)
    path.unlink()
    path, intent = only_record(directory, "intents", core.SubmissionIntent)
    path.unlink()
    return intent


def tamper_forged_foundation_call(core, directory):
    _, call = record_paths(directory, "foundation-calls", core.FinancialCall)[0]
    binding = call.binding.model_copy(update={"snapshot_sha256": NOT_IN_CHAIN})
    put_record(
        directory,
        "foundation-calls",
        call.model_copy(update={"binding": binding, "call_id": "forged"}),
    )


def tamper_forged_owner_session(core, directory):
    session = core.OwnerSession(
        session_id="owner-session:" + "c" * 32,
        index=1,
        binding=forged_owner_binding(core, directory),
        normalized_grant_json="{}",
        access_manifest_json="{}",
    )
    put_record(directory, "owner-sessions", session)


def tamper_forged_owner_read_unknown_session(core, directory):
    read = core.OwnerAccessRead(
        session_id="owner-session:" + "d" * 32,
        sequence=1,
        binding=forged_owner_binding(core, directory),
        access_manifest_json="{}",
    )
    put_record(directory, "owner-reads", read)


def tamper_forged_foundation_read(core, directory):
    _, call = record_paths(directory, "foundation-calls", core.FinancialCall)[0]
    binding = call.binding.model_copy(update={"snapshot_sha256": NOT_IN_CHAIN})
    put_record(
        directory,
        "foundation-reads",
        core.InputRead(binding=binding, sequence=1, inputs_sha256="ef" * 32, body="{}"),
    )


def tamper_deleted_intent_outcome_kept(core, directory):
    path, _ = only_record(directory, "intents", core.SubmissionIntent)
    path.unlink()


def tamper_pending_intent_snapshot_before_outside_chain(core, directory):
    intent = lose_outcome_and_intent(core, directory)
    put_record(
        directory, "intents", intent.model_copy(update={"snapshot_before_sha256": NOT_IN_CHAIN})
    )


def tamper_pending_intent_payload_not_utf8(core, directory):
    intent = lose_outcome_and_intent(core, directory)
    bad = b"\xff\xfe not utf-8"
    bad_digest = hashlib.sha256(bad).hexdigest()
    (directory / AUDIT / "payloads" / bad_digest).write_bytes(bad)
    bound = intent.binding.model_copy(update={"raw_payload_sha256": bad_digest})
    put_record(directory, "bindings", bound)
    put_record(directory, "intents", intent.model_copy(update={"binding": bound}))


def tamper_pending_binding_names_absent_foundation_read(core, directory):
    intent = lose_outcome_and_intent(core, directory)
    bound = intent.binding.model_copy(update={"input_read_hashes": (NOT_IN_CHAIN,)})
    put_record(directory, "bindings", bound)
    put_record(directory, "intents", intent.model_copy(update={"binding": bound}))


def tamper_deleted_outcome_after_next_begin(core, directory):
    path, _ = only_record(directory, "outcomes", core.SubmissionOutcome)
    path.unlink()


def tamper_kind_path_is_a_file(core, directory):
    shutil.rmtree(directory / AUDIT / "outcomes")
    (directory / AUDIT / "outcomes").write_bytes(b"x")


def sorted_begins(core, directory):
    return sorted(audit_records(core, directory, "begins", core.BeginRecord), key=lambda b: b.index)


def tamper_duplicate_begin_edge(core, directory):
    begins = sorted_begins(core, directory)
    assert begins[-1].error_code is None
    put_record(directory, "begins", begins[-1].model_copy(update={"index": len(begins) + 1}))


def forge_begin(core, directory, module_id, snapshot_before_sha256):
    begins = audit_records(core, directory, "begins", core.BeginRecord)
    head = current_snapshot(directory).content_hash()
    put_record(
        directory,
        "begins",
        core.BeginRecord(
            index=len(begins) + 1,
            module_id=module_id,
            snapshot_before_sha256=snapshot_before_sha256,
            snapshot_after_sha256=head,
            ticket_id="forged",
            attempt=0,
            error_code=None,
        ),
    )


def tamper_forged_cp1b_begin_from_head_with_cp1_pending(core, directory):
    forge_begin(core, directory, "CP-1B", current_snapshot(directory).content_hash())


def tamper_forged_cp1_begin_from_initial_snapshot(core, directory):
    forge_begin(core, directory, "CP-1", sorted_begins(core, directory)[0].snapshot_before_sha256)


def tamper_forged_refusal_begin_from_initial_snapshot(core, directory):
    # A `not_authorized` begin claimed from the initial snapshot: the core's replay refuses
    # CP-1 there for an unrun upstream, not for authorization, so the record is forged.
    begins = sorted_begins(core, directory)
    initial = begins[0].snapshot_before_sha256
    put_record(
        directory,
        "begins",
        core.BeginRecord(
            index=len(begins) + 1,
            module_id="CP-1",
            snapshot_before_sha256=initial,
            snapshot_after_sha256=initial,
            ticket_id=None,
            attempt=None,
            error_code="not_authorized",
        ),
    )


def cp0_blob(directory, role):
    snapshot = current_snapshot(directory)
    if role == "pack":
        return snapshot.pack_sha256
    (attempt,) = [a for a in snapshot.attempts if a.module_id == "CP-0"]
    if role == "result":
        return attempt.result_sha256
    return getattr(attempt.steps[0], role + "_sha256")


def deleted_blob(role):
    def tamper(core, directory):
        (directory / "blobs" / cp0_blob(directory, role)).unlink()

    return tamper


OPEN_TAMPERS = {
    "T1_forged_foundation_call_snapshot_outside_chain": tamper_forged_foundation_call,
    "T2_forged_owner_session_snapshot_outside_chain": tamper_forged_owner_session,
    "T3_forged_owner_read_unknown_session": tamper_forged_owner_read_unknown_session,
    "T4_forged_foundation_read_snapshot_outside_chain": tamper_forged_foundation_read,
    "T5_deleted_intent_outcome_kept": tamper_deleted_intent_outcome_kept,
    "T6_pending_intent_snapshot_before_outside_chain": (
        tamper_pending_intent_snapshot_before_outside_chain
    ),
    "T7_pending_intent_payload_not_utf8": tamper_pending_intent_payload_not_utf8,
    "T8_deleted_pack_blob": deleted_blob("pack"),
    "T8_deleted_payload_blob": deleted_blob("payload"),
    "T8_deleted_step_output_blob": deleted_blob("output"),
    "T8_deleted_result_blob": deleted_blob("result"),
    "U1_pending_binding_names_absent_foundation_read": (
        tamper_pending_binding_names_absent_foundation_read
    ),
    "U3_kind_path_is_a_file": tamper_kind_path_is_a_file,
    "T6c_deleted_outcome_after_next_begin": tamper_deleted_outcome_after_next_begin,
    "T9_duplicate_begin_edge": tamper_duplicate_begin_edge,
    "B_forged_cp1b_begin_from_head_with_cp1_pending": (
        tamper_forged_cp1b_begin_from_head_with_cp1_pending
    ),
    "B_forged_cp1_begin_from_initial_snapshot": tamper_forged_cp1_begin_from_initial_snapshot,
    "B_forged_refusal_begin_from_initial_snapshot": (
        tamper_forged_refusal_begin_from_initial_snapshot
    ),
}


@pytest.mark.parametrize("tamper", OPEN_TAMPERS)
def test_tampered_or_deleted_stored_evidence_at_open_refuses_identity_mismatch(tmp_path, tamper):
    core = api()
    base = tmp_path / "base" / "owner"
    cp0_to_source_context(core, base)
    directory = tmp_path / "tampered" / "owner"
    shutil.copytree(base, directory)
    OPEN_TAMPERS[tamper](core, directory)
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, directory)
    assert error.value.code == "identity_mismatch"


@pytest.mark.parametrize("defect", ["garbage", "deleted", "directory"])
def test_sealed_reopen_with_unreadable_receipt_refuses_identity_mismatch(tmp_path, defect):
    core = api()
    base = tmp_path / "base" / "owner"
    drive_fresh_foundation(core, base, "E-REQUIRED-CP1-MISSING").write_receipt(
        tmp_path / "base" / "receipt.json"
    )
    directory = tmp_path / "tampered" / "owner"
    shutil.copytree(base, directory)
    receipt = directory / AUDIT / "owner-receipt.json"
    if defect == "garbage":
        receipt.write_bytes(b"{not json")
    elif defect == "deleted":
        receipt.unlink()
    else:
        receipt.unlink()
        receipt.mkdir()
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, directory)
    assert error.value.code == "identity_mismatch"


def test_duplicate_refusal_begin_is_refused_by_open_write_receipt_and_the_verifier(tmp_path):
    core = api()
    from deploy_vii.execution import Execution

    live = tmp_path / "live" / "owner"
    workflow = drive_fresh_foundation(core, live, "E-REQUIRED-CP1-MISSING")
    begins = sorted_begins(core, live)
    assert [b.error_code for b in begins] == [None, "not_authorized"]
    put_record(live, "begins", begins[-1].model_copy(update={"index": len(begins) + 1}))
    with pytest.raises(core.OwnerError) as error:
        workflow.write_receipt(tmp_path / "live" / "receipt.json")
    assert error.value.code == "identity_mismatch"
    assert not (live / AUDIT / "owner-receipt.json").exists()
    assert not (tmp_path / "live" / "receipt.json").exists()
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, live)
    assert error.value.code == "identity_mismatch"

    sealed = tmp_path / "sealed" / "owner"
    receipt = drive_fresh_foundation(core, sealed, "E-REQUIRED-CP1-MISSING").write_receipt(
        tmp_path / "sealed" / "receipt.json"
    )
    duplicate = receipt.begins[-1].model_copy(update={"index": len(receipt.begins) + 1})
    put_record(sealed, "begins", duplicate)
    forged = receipt.model_copy(
        update={
            "begins": (*receipt.begins, duplicate),
            "audit_inventory": core._inventory(Execution(sealed)),
        }
    )
    (sealed / AUDIT / "owner-receipt.json").write_bytes(forged.model_dump_json().encode())
    (sealed / AUDIT / "owner-receipt.sha256").write_bytes(forged.content_hash().encode("ascii"))
    with pytest.raises(core.OwnerError) as error:
        core.verify_earnings_owner_receipt(Execution(sealed), forged)
    assert error.value.code == "identity_mismatch"


def reorder_begins_refusal_first(core, directory):
    """Swap the two begin indices of a complete negative run: refusal 1, CP-0 begin 2."""
    paths = record_paths(directory, "begins", core.BeginRecord)
    assert sorted(str(b.error_code) for _, b in paths) == ["None", "not_authorized"]
    for path, _ in paths:
        path.unlink()
    reordered = [b.model_copy(update={"index": 3 - b.index}) for _, b in paths]
    for begin in reordered:
        put_record(directory, "begins", begin)
    return tuple(sorted(reordered, key=lambda b: b.index))


def test_reordered_begins_with_the_refusal_first_are_refused_by_open_write_receipt_and_the_verifier(
    tmp_path,
):
    core = api()
    from deploy_vii.execution import Execution

    live = tmp_path / "live" / "owner"
    workflow = drive_fresh_foundation(core, live, "E-REQUIRED-CP1-MISSING")
    begins = sorted_begins(core, live)
    assert [b.error_code for b in begins] == [None, "not_authorized"]
    reorder_begins_refusal_first(core, live)
    with pytest.raises(core.OwnerError) as error:
        workflow.write_receipt(tmp_path / "live" / "receipt.json")
    assert error.value.code == "identity_mismatch"
    assert not (live / AUDIT / "owner-receipt.json").exists()
    assert not (tmp_path / "live" / "receipt.json").exists()
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, live)
    assert error.value.code == "identity_mismatch"

    sealed = tmp_path / "sealed" / "owner"
    receipt = drive_fresh_foundation(core, sealed, "E-REQUIRED-CP1-MISSING").write_receipt(
        tmp_path / "sealed" / "receipt.json"
    )
    reordered = reorder_begins_refusal_first(core, sealed)
    forged = receipt.model_copy(
        update={"begins": reordered, "audit_inventory": core._inventory(Execution(sealed))}
    )
    (sealed / AUDIT / "owner-receipt.json").write_bytes(forged.model_dump_json().encode())
    (sealed / AUDIT / "owner-receipt.sha256").write_bytes(forged.content_hash().encode("ascii"))
    with pytest.raises(core.OwnerError) as error:
        core.verify_earnings_owner_receipt(Execution(sealed), forged)
    assert error.value.code == "identity_mismatch"


def crash_before_cp1_begin_record(core, directory, monkeypatch):
    """A fresh positive run whose CP-0 review is valid; the process dies after the core
    begins CP-1 and before `_begin` retains that BeginRecord."""
    pack = pack_for("E-QOQ-FLAT")
    workflow = core.EarningsWorkflow.create(
        directory, pack, case_manifest=CASE_MANIFEST, case_id="E-QOQ-FLAT"
    )
    read_foundation_sources(workflow)
    original = core._retain

    def crashed_retain(store, kind, record):
        if kind == "begins":
            raise OSError("injected crash before the begin record")
        return original(store, kind, record)

    monkeypatch.setattr(core, "_retain", crashed_retain)
    with pytest.raises(OSError):
        workflow.submit_review(foundation_review(pack))
    monkeypatch.setattr(core, "_retain", original)
    return pack


@pytest.mark.parametrize("loss", ["crash", "deleted"])
def test_lost_later_begin_record_is_recovered_by_core_replay_and_the_run_resumes(
    tmp_path, monkeypatch, loss
):
    core = api()
    from test_financial_workflow import context

    from deploy_vii.execution import Execution

    directory = tmp_path / "owner"
    if loss == "crash":
        pack = crash_before_cp1_begin_record(core, directory, monkeypatch)
        lost = None
    else:
        pack = pack_for("E-QOQ-FLAT")
        cp0_to_source_context(core, directory)
        path, lost = max(
            record_paths(directory, "begins", core.BeginRecord), key=lambda p: p[1].index
        )
        assert lost.module_id == "CP-1"
        path.unlink()
    before = Execution(directory).read()
    (cp1,) = [a for a in before.attempts if a.status == "pending"]
    assert cp1.module_id == "CP-1"
    assert [b.module_id for b in sorted_begins(core, directory)] == ["CP-0"]

    reopened = reopen_workflow(core, directory)
    assert Execution(directory).read() == before  # Recovered; the begin is not repeated.
    begins = sorted_begins(core, directory)
    expected = core.BeginRecord(
        index=2,
        module_id="CP-1",
        snapshot_before_sha256=before.parent,
        snapshot_after_sha256=before.content_hash(),
        ticket_id=cp1.ticket_id,
        attempt=0,
        error_code=None,
    )
    assert begins == [begins[0], expected]
    if lost is not None:
        assert expected == lost
    assert (reopened.state().phase, reopened.state().ticket_id) == ("source_context", cp1.ticket_id)
    # The recovered run resumes where the crash left it: the CP-1 source-context epoch.
    read_foundation_sources(reopened)
    assert (
        reopened.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})["status"]
        == "ok"
    )
    assert reopened.submit_review(context(pack)).disposition == "valid"
    assert reopened.state().phase == "financials"
    assert len(sorted_begins(core, directory)) == 2
    assert reopen_workflow(core, directory).state().phase == "financials"


def test_opener_initialised_before_a_concurrent_openers_crashed_core_begin_opens_or_writes_nothing(
    tmp_path, monkeypatch
):
    # Opener A initialises (reads the head X) before taking the lock; opener B then takes
    # the lock first, core-begins CP-1 and dies before its BeginRecord. A must read the
    # head again under the lock: it then recovers B's begin and opens, instead of writing
    # the genuine record and refusing on a stale binding. A refusal would be acceptable
    # only if it left the file tree as B's crash left it.
    from deploy_vii.execution import Execution

    core = api()
    directory = tmp_path / "owner"
    cp0_to_source_context(core, directory)
    path, _ = max(record_paths(directory, "begins", core.BeginRecord), key=lambda p: p[1].index)
    path.unlink()
    head = Execution(directory).read()
    x = head.parent
    (directory / "current").write_text(x + "\n", encoding="ascii")
    (directory / "snapshots" / (head.content_hash() + ".json")).unlink()

    class Crash(BaseException):
        pass

    original_retain = core._retain
    original_locked = core.EarningsWorkflow._locked
    after_b = []

    def crashing_retain(store, kind, record):
        if kind == "begins":
            raise Crash
        return original_retain(store, kind, record)

    def locked(self, *, inspect_sealed=False):
        if not after_b and self._current_sha256 == x:
            monkeypatch.setattr(core.EarningsWorkflow, "_locked", original_locked)
            monkeypatch.setattr(core, "_retain", crashing_retain)
            try:
                with pytest.raises(Crash):
                    reopen_workflow(core, directory)
            finally:
                monkeypatch.setattr(core, "_retain", original_retain)
                monkeypatch.setattr(core.EarningsWorkflow, "_locked", locked)
            after_b.append(file_tree(directory))
            # B moved the head: the head A read before the lock is stale.
            assert Execution(directory).read().content_hash() != x
        return original_locked(self, inspect_sealed=inspect_sealed)

    monkeypatch.setattr(core.EarningsWorkflow, "_locked", locked)
    try:
        opened = reopen_workflow(core, directory)
    except core.OwnerError:
        assert after_b
        assert file_tree(directory) == after_b[0]
        return
    assert after_b
    (pending,) = [a for a in Execution(directory).read().attempts if a.status == "pending"]
    assert pending.module_id == "CP-1"
    assert opened.state().ticket_id == pending.ticket_id
    assert [b.module_id for b in sorted_begins(core, directory)] == ["CP-0", "CP-1"]


MISSING_CASE = "E-REQUIRED-CP1-MISSING"


def bounded_missing_store(core, directory):
    """A completed, not yet sealed `cp1_not_authorized` store on the bounded transport."""
    pack = pack_for(MISSING_CASE)
    workflow = core.EarningsWorkflow.create(
        directory,
        pack,
        case_manifest=CASE_MANIFEST,
        case_id=MISSING_CASE,
        participant="bounded-component",
        transport="bounded-json-lines/1",
    )
    for source in ("identity", "financial"):
        workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
    assert workflow.submit_review(foundation_review(pack, True)).disposition == "valid"
    assert workflow.state().phase == "complete"
    return workflow


def open_bounded(core, directory):
    return core.EarningsWorkflow.open(
        directory,
        case_manifest=CASE_MANIFEST,
        participant="bounded-component",
        transport="bounded-json-lines/1",
    )


def serve_frames(core, workflow, frames, destination):
    source, sink = io.BytesIO(frames), io.BytesIO()
    reader = io.TextIOWrapper(source, encoding="ascii", errors="ignore", newline=None)
    writer = io.TextIOWrapper(sink, encoding="ascii", errors="strict", newline="\r\n")
    try:
        core.serve_json_lines(workflow, reader, writer, destination=destination)
        writer.flush()
        return sink.getvalue()
    finally:
        reader.detach()
        writer.detach()


class ReceiptCommitCrash(BaseException):
    pass


def crash_before_receipt_commit(core, monkeypatch, action):
    """Run `action` with `_put` dying on `owner-receipt.sha256`, after the receipt json."""
    original = core._put

    def crashing_put(path, raw):
        if path.name == "owner-receipt.sha256":
            raise ReceiptCommitCrash
        return original(path, raw)

    with monkeypatch.context() as patch:
        patch.setattr(core, "_put", crashing_put)
        with pytest.raises(ReceiptCommitCrash):
            action()


def test_instance_opened_before_another_instances_seal_refuses_receipt_and_frames(tmp_path):
    from deploy_vii.execution import Execution

    core = api()
    directory = tmp_path / "owner"
    sealer = bounded_missing_store(core, directory)
    late = open_bounded(core, directory)
    assert late._sealed is False
    receipt = sealer.write_receipt(tmp_path / "sealer.json")
    destination = tmp_path / "late.json"
    with pytest.raises(core.OwnerError) as refused:
        late.write_receipt(destination)
    assert refused.value.code == "not_permitted" and not destination.exists()
    tree = file_tree(directory)
    inventory = core._inventory(Execution(directory))
    with pytest.raises(core.OwnerError) as frame:
        serve_frames(core, late, b'{"op":"state"}\n', tmp_path / "frame.json")
    assert frame.value.code == "not_permitted"
    assert file_tree(directory) == tree
    assert core._inventory(Execution(directory)) == inventory
    core.verify_earnings_owner_receipt(Execution(directory), receipt)
    assert open_bounded(core, directory).state().phase == "complete"


def test_opener_whose_lock_is_won_after_a_seal_takes_the_sealed_branch(tmp_path, monkeypatch):
    from deploy_vii.execution import Execution

    core = api()
    directory = tmp_path / "owner"
    sealer = bounded_missing_store(core, directory)
    original_locked = core.EarningsWorkflow._locked
    sealed = []

    def locked(self, *, inspect_sealed=False):
        if not sealed and inspect_sealed:
            # `_initialize` has run (unsealed); the other instance seals before the lock.
            monkeypatch.setattr(core.EarningsWorkflow, "_locked", original_locked)
            sealed.append(sealer.write_receipt(tmp_path / "sealer.json"))
            sealed.append(file_tree(directory))
            monkeypatch.setattr(core.EarningsWorkflow, "_locked", locked)
        return original_locked(self, inspect_sealed=inspect_sealed)

    monkeypatch.setattr(core.EarningsWorkflow, "_locked", locked)
    opened = open_bounded(core, directory)
    assert sealed
    assert opened._sealed is True
    assert (opened.state().phase, opened.state().outcome) == ("complete", "cp1_not_authorized")
    assert file_tree(directory) == sealed[1]
    core.verify_earnings_owner_receipt(Execution(directory), sealed[0])


def committed_receipt(core, directory):
    from deploy_vii.execution import Execution

    audit = directory / "earnings-owner-audit"
    raw = (audit / "owner-receipt.json").read_bytes()
    receipt = core.EarningsOwnerReceipt.model_validate_json(raw)
    assert (audit / "owner-receipt.sha256").read_bytes() == receipt.content_hash().encode("ascii")
    core.verify_earnings_owner_receipt(Execution(directory), receipt)
    return raw


def test_transport_close_retry_after_a_crash_before_the_receipt_commit_seals(tmp_path, monkeypatch):
    core = api()
    directory = tmp_path / "owner"
    workflow = bounded_missing_store(core, directory)
    crash_before_receipt_commit(
        core,
        monkeypatch,
        lambda: serve_frames(core, workflow, b'{"op":"close"}\n', tmp_path / "first.json"),
    )
    audit = directory / "earnings-owner-audit"
    assert (audit / "owner-receipt.json").exists()
    assert not (audit / "owner-receipt.sha256").exists()
    reopened = open_bounded(core, directory)
    assert reopened._sealed is False
    retry = tmp_path / "retry.json"
    reply = serve_frames(core, reopened, b'{"op":"close"}\n', retry)
    assert b'"status":"ok"' in reply.replace(b" ", b"")
    assert retry.read_bytes() == committed_receipt(core, directory)
    assert open_bounded(core, directory)._sealed is True


def test_python_api_write_receipt_retry_after_a_crash_before_the_receipt_commit_seals(
    tmp_path, monkeypatch
):
    core = api()
    directory = tmp_path / "owner"
    workflow = bounded_missing_store(core, directory)
    # A frame served after the reopen retains one more message, so the retried receipt
    # differs from the json the crash left behind.
    crash_before_receipt_commit(
        core,
        monkeypatch,
        lambda: serve_frames(core, workflow, b'{"op":"close"}\n', tmp_path / "first.json"),
    )
    stale = (directory / "earnings-owner-audit/owner-receipt.json").read_bytes()
    reopened = open_bounded(core, directory)
    serve_frames(core, reopened, b'{"op":"state"}\n', tmp_path / "unused.json")
    retry = tmp_path / "retry.json"
    reopened.write_receipt(retry)
    committed = committed_receipt(core, directory)
    assert committed != stale
    assert retry.read_bytes() == committed


def test_python_api_close_retry_after_a_crash_before_the_receipt_commit_seals(
    tmp_path, monkeypatch
):
    core = api()
    directory = tmp_path / "owner"
    workflow = drive_fresh_foundation(core, directory, MISSING_CASE)
    crash_before_receipt_commit(
        core, monkeypatch, lambda: workflow.write_receipt(tmp_path / "first.json")
    )
    reopened = reopen_workflow(core, directory)
    retry = tmp_path / "retry.json"
    reopened.write_receipt(retry)
    assert retry.read_bytes() == committed_receipt(core, directory)


def test_receipt_retry_to_a_differing_destination_refuses_and_writes_nothing(tmp_path, monkeypatch):
    core = api()
    directory = tmp_path / "owner"
    workflow = bounded_missing_store(core, directory)
    crash_before_receipt_commit(
        core,
        monkeypatch,
        lambda: serve_frames(core, workflow, b'{"op":"close"}\n', tmp_path / "first.json"),
    )
    reopened = open_bounded(core, directory)
    serve_frames(core, reopened, b'{"op":"state"}\n', tmp_path / "unused.json")
    tree = file_tree(directory)
    differing = tmp_path / "differing.json"
    differing.write_bytes(b"not the receipt")
    with pytest.raises(core.OwnerError) as refused:
        reopened.write_receipt(differing)
    assert refused.value.code == "identity_mismatch"
    assert differing.read_bytes() == b"not the receipt"
    assert file_tree(directory) == tree
    assert not (directory / "earnings-owner-audit/owner-receipt.sha256").exists()
    # The refusal sealed nothing: a destination that matches still commits.
    reopened.write_receipt(tmp_path / "retry.json")
    committed_receipt(core, directory)


def crash_after_transport_close_to(core, monkeypatch, directory, destination):
    workflow = bounded_missing_store(core, directory)
    crash_before_receipt_commit(
        core,
        monkeypatch,
        lambda: serve_frames(core, workflow, b'{"op":"close"}\n', destination),
    )
    assert destination.exists()
    assert not (directory / "earnings-owner-audit/owner-receipt.sha256").exists()


def test_transport_close_retry_to_the_same_destination_after_a_crash_seals(tmp_path, monkeypatch):
    core = api()
    directory = tmp_path / "owner"
    destination = tmp_path / "export.json"
    crash_after_transport_close_to(core, monkeypatch, directory, destination)
    reply = serve_frames(core, open_bounded(core, directory), b'{"op":"close"}\n', destination)
    assert b'"status":"ok"' in reply.replace(b" ", b"")
    assert destination.read_bytes() == committed_receipt(core, directory)


def test_python_api_retry_to_the_same_destination_after_a_crash_and_a_frame_seals(
    tmp_path, monkeypatch
):
    core = api()
    directory = tmp_path / "owner"
    destination = tmp_path / "export.json"
    crash_after_transport_close_to(core, monkeypatch, directory, destination)
    reopened = open_bounded(core, directory)
    serve_frames(core, reopened, b'{"op":"state"}\n', tmp_path / "unused.json")
    reopened.write_receipt(destination)
    assert destination.read_bytes() == committed_receipt(core, directory)
    assert open_bounded(core, directory)._sealed is True


def test_foreign_destination_differing_from_both_receipts_refuses_and_changes_nothing(
    tmp_path, monkeypatch
):
    core = api()
    directory = tmp_path / "owner"
    crash_after_transport_close_to(core, monkeypatch, directory, tmp_path / "first.json")
    reopened = open_bounded(core, directory)
    serve_frames(core, reopened, b'{"op":"state"}\n', tmp_path / "unused.json")
    foreign = tmp_path / "foreign.json"
    foreign.write_bytes((tmp_path / "first.json").read_bytes()[:-1] + b" ")
    before = foreign.read_bytes()
    tree = file_tree(directory)
    with pytest.raises(core.OwnerError) as refused:
        reopened.write_receipt(foreign)
    assert refused.value.code == "identity_mismatch"
    assert foreign.read_bytes() == before
    assert file_tree(directory) == tree


def test_crash_on_the_json_put_of_a_same_destination_retry_still_seals_on_the_next_retry(
    tmp_path, monkeypatch
):
    core = api()
    directory = tmp_path / "owner"
    destination = tmp_path / "export.json"
    crash_after_transport_close_to(core, monkeypatch, directory, destination)
    reopened = open_bounded(core, directory)
    serve_frames(core, reopened, b'{"op":"state"}\n', tmp_path / "unused.json")
    original = core._put

    def crashing_put(path, raw):
        if path.name == "owner-receipt.json" and path.parent.name == "earnings-owner-audit":
            raise ReceiptCommitCrash
        return original(path, raw)

    with monkeypatch.context() as patch:
        patch.setattr(core, "_put", crashing_put)
        with pytest.raises(ReceiptCommitCrash):
            reopened.write_receipt(destination)
    retry = open_bounded(core, directory)
    reply = serve_frames(core, retry, b'{"op":"close"}\n', destination)
    assert b'"status":"ok"' in reply.replace(b" ", b"")
    assert destination.read_bytes() == committed_receipt(core, directory)


def test_crash_on_the_destination_unlink_of_a_same_destination_retry_still_seals(
    tmp_path, monkeypatch
):
    core = api()
    directory = tmp_path / "owner"
    destination = tmp_path / "export.json"
    crash_after_transport_close_to(core, monkeypatch, directory, destination)
    original = Path.unlink

    def crashing_unlink(path, missing_ok=False):
        if path == destination:
            raise ReceiptCommitCrash
        return original(path, missing_ok=missing_ok)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", crashing_unlink)
        with pytest.raises(ReceiptCommitCrash):
            serve_frames(core, open_bounded(core, directory), b'{"op":"close"}\n', destination)
    reply = serve_frames(core, open_bounded(core, directory), b'{"op":"close"}\n', destination)
    assert b'"status":"ok"' in reply.replace(b" ", b"")
    assert destination.read_bytes() == committed_receipt(core, directory)


def refuse_a_foreign_file_planted_as_the_uncommitted_receipt(
    tmp_path, monkeypatch, plant_uncommitted
):
    core = api()
    directory = tmp_path / "owner"
    crash_after_transport_close_to(core, monkeypatch, directory, tmp_path / "first.json")
    reopened = open_bounded(core, directory)
    serve_frames(core, reopened, b'{"op":"state"}\n', tmp_path / "unused.json")
    foreign = tmp_path / "foreign.json"
    foreign.write_bytes(b"an operator file, not a receipt\n")
    pending = directory / "earnings-owner-audit/owner-receipt.json"
    pending.unlink()
    plant_uncommitted(pending, foreign)
    before = foreign.read_bytes()
    tree = file_tree(directory)
    with pytest.raises(core.OwnerError) as refused:
        reopened.write_receipt(foreign)
    assert refused.value.code == "identity_mismatch"
    assert foreign.read_bytes() == before
    assert file_tree(directory) == tree


def test_a_symlink_planted_as_the_uncommitted_receipt_never_authorises_overwriting_its_target(
    tmp_path, monkeypatch
):
    refuse_a_foreign_file_planted_as_the_uncommitted_receipt(
        tmp_path, monkeypatch, lambda pending, foreign: pending.symlink_to(foreign)
    )


def test_a_regular_file_planted_as_the_uncommitted_receipt_never_authorises_overwriting_a_match(
    tmp_path, monkeypatch
):
    refuse_a_foreign_file_planted_as_the_uncommitted_receipt(
        tmp_path,
        monkeypatch,
        lambda pending, foreign: pending.write_bytes(foreign.read_bytes()),
    )


def test_another_stores_uncommitted_receipt_planted_as_this_ones_is_never_overwritten(
    tmp_path, monkeypatch
):
    core = api()
    directory = tmp_path / "owner"
    foreign = tmp_path / "foreign.json"
    crash_after_transport_close_to(core, monkeypatch, directory, tmp_path / "first.json")
    crash_after_transport_close_to(core, monkeypatch, tmp_path / "other", foreign)
    reopened = open_bounded(core, directory)
    serve_frames(core, reopened, b'{"op":"state"}\n', tmp_path / "unused.json")
    pending = directory / "earnings-owner-audit/owner-receipt.json"
    pending.write_bytes(foreign.read_bytes())
    before = foreign.read_bytes()
    tree = file_tree(directory)
    with pytest.raises(core.OwnerError) as refused:
        reopened.write_receipt(foreign)
    assert refused.value.code == "identity_mismatch"
    assert foreign.read_bytes() == before
    assert file_tree(directory) == tree


def tamper_non_last_edge_uncovered(core, directory):
    # Delete the CP-0 begin and renumber the CP-1 begin to 1: contiguous, one record, and
    # the only uncovered chain edge is the first one, which recovery must never synthesise.
    paths = record_paths(directory, "begins", core.BeginRecord)
    (_, last) = max(paths, key=lambda p: p[1].index)
    assert last.module_id == "CP-1" and len(paths) == 2
    for path, _ in paths:
        path.unlink()
    put_record(directory, "begins", last.model_copy(update={"index": 1}))


def tamper_head_adds_two_pending_attempts(core, directory):
    # The crash state (CP-1 begin record lost) with a forged head that appends a second
    # pending attempt to the same parent; only a core begin's single attempt is recoverable.
    (last_path, last) = max(
        record_paths(directory, "begins", core.BeginRecord), key=lambda p: p[1].index
    )
    assert last.module_id == "CP-1"
    last_path.unlink()
    head = current_snapshot(directory)
    (pending,) = [a for a in head.attempts if a.status == "pending"]
    write_head(
        directory,
        head.model_copy(
            update={
                "attempts": (*head.attempts, pending.model_copy(update={"ticket_id": "forged"}))
            }
        ),
    )


def write_head(directory, snapshot):
    """Store `snapshot` and make it the journal head, as a forger with file access would."""
    raw = snapshot.model_dump_json().encode()
    digest = hashlib.sha256(raw).hexdigest()
    (directory / "snapshots" / (digest + ".json")).write_bytes(raw)
    (directory / "current").write_text(digest + "\n", encoding="ascii")


def file_tree(directory):
    """Every file under `directory` by relative path, with its bytes."""
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def forge_head_in_crash_state(core, directory, added):
    """Delete the CP-1 begin record and replace the head by its parent plus `added` attempts.

    `added(pending, before)` receives the pending attempt the lost core begin appended
    and the parent snapshot; a genuine crash state would return `(pending,)`, so each
    case alters exactly one property of what a core begin writes.
    """
    from deploy_vii.execution import Execution

    (last_path, last) = max(
        record_paths(directory, "begins", core.BeginRecord), key=lambda p: p[1].index
    )
    assert last.module_id == "CP-1"
    last_path.unlink()
    head = current_snapshot(directory)
    (pending,) = [a for a in head.attempts if a.status == "pending"]
    before = core._snapshot(Execution(directory), head.parent)
    write_head(
        directory,
        before.model_copy(
            update={
                "parent": before.content_hash(),
                "attempts": (*before.attempts, *added(pending, before)),
            }
        ),
    )


def tamper_head_adds_zero_attempts(core, directory):
    forge_head_in_crash_state(core, directory, lambda pending, before: ())


def tamper_head_adds_out_of_set_module(core, directory):
    forge_head_in_crash_state(
        core, directory, lambda pending, before: (pending.model_copy(update={"module_id": "CP-5"}),)
    )


def tamper_head_adds_forged_inputs(core, directory):
    forge_head_in_crash_state(
        core, directory, lambda pending, before: (pending.model_copy(update={"inputs": ()}),)
    )


def tamper_head_ticket_duplicates_the_cp0_ticket(core, directory):
    def added(pending, before):
        (cp0,) = [a for a in before.attempts if a.module_id == "CP-0"]
        return (pending.model_copy(update={"ticket_id": cp0.ticket_id}),)

    forge_head_in_crash_state(core, directory, added)


RECOVERY_REFUSALS = {
    "non_last_edge_uncovered": tamper_non_last_edge_uncovered,
    "head_adds_two_pending_attempts": tamper_head_adds_two_pending_attempts,
    "head_adds_zero_attempts": tamper_head_adds_zero_attempts,
    "head_adds_out_of_set_module": tamper_head_adds_out_of_set_module,
    "head_adds_forged_inputs": tamper_head_adds_forged_inputs,
}


@pytest.mark.parametrize("defect", RECOVERY_REFUSALS)
def test_begin_recovery_refuses_a_non_last_gap_and_heads_no_core_begin_writes(tmp_path, defect):
    core = api()
    directory = tmp_path / "owner"
    cp0_to_source_context(core, directory)
    records_before = sorted(p.name for p in (directory / AUDIT / "begins").iterdir())
    RECOVERY_REFUSALS[defect](core, directory)
    tampered = file_tree(directory)
    assert sorted(p.name for p in (directory / AUDIT / "begins").iterdir()) != records_before
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, directory)
    assert error.value.code == "identity_mismatch"
    # Refusal synthesised nothing: the store is exactly as tampered, names and bytes.
    assert file_tree(directory) == tampered


@pytest.mark.parametrize("evidence", ["foundation_calls", "refused_submission"])
def test_deleted_begin_record_with_records_bound_to_its_head_is_not_recovered(tmp_path, evidence):
    core = api()
    from test_financial_workflow import context

    directory = tmp_path / "owner"
    workflow = cp0_to_source_context(core, directory)
    read_foundation_sources(workflow)
    if evidence == "refused_submission":
        # A context review without a search_pack call is refused: its intent and outcome
        # are bound to the head and the head does not move.
        assert workflow.submit_review(context(pack_for("E-QOQ-FLAT"))).disposition == "refused"
    head = current_snapshot(directory).content_hash()
    (path, lost) = max(
        record_paths(directory, "begins", core.BeginRecord), key=lambda p: p[1].index
    )
    assert (lost.module_id, lost.snapshot_after_sha256) == ("CP-1", head)
    calls = audit_records(core, directory, "foundation-calls", core.FinancialCall)
    assert len([c for c in calls if c.binding.snapshot_sha256 == head]) == 2
    if evidence == "refused_submission":
        intents = audit_records(core, directory, "intents", core.SubmissionIntent)
        (intent,) = [i for i in intents if i.snapshot_before_sha256 == head]
        outcomes = audit_records(core, directory, "outcomes", core.SubmissionOutcome)
        (outcome,) = [o for o in outcomes if o.intent_sha256 == intent.content_hash()]
        assert (outcome.disposition, outcome.snapshot_after_sha256) == ("refused", head)
    # Records bound to a head are written only after its begin record is retained, so the
    # record's absence is a deletion, not the crash window: nothing is synthesised.
    path.unlink()
    tampered = file_tree(directory)
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, directory)
    assert error.value.code == "identity_mismatch"
    assert file_tree(directory) == tampered


def tamper_later_begins_of_a_repair_run_deleted(core, directory):
    """Delete begins 2 and 3 (CP-1 attempts 0 and 1) of a run whose attempt 1 is pending.

    The surviving record and the head look like the crash window of begin 2, but the
    chain holds two uncovered begin edges; a record synthesised for the last one would
    be mis-indexed and collide with the originals were they restored.
    """
    for path, begin in record_paths(directory, "begins", core.BeginRecord):
        if begin.index > 1:
            path.unlink()


@pytest.mark.parametrize(
    "tamper", ["later_begins_deleted", "head_ticket_duplicates_the_cp0_ticket"]
)
def test_refused_open_leaves_a_tampered_store_byte_identical(tmp_path, tamper):
    core = api()
    directory = tmp_path / "owner"
    workflow = cp0_to_source_context(core, directory)
    if tamper == "later_begins_deleted":
        for payload in ("{}", "{ }"):
            read_foundation_sources(workflow)
            assert workflow.submit_review(payload).disposition == "invalid"
        assert [(b.module_id, b.attempt) for b in sorted_begins(core, directory)] == [
            ("CP-0", 0),
            ("CP-1", 0),
            ("CP-1", 1),
        ]
        assert workflow.state().attempt == 1
        tamper_later_begins_of_a_repair_run_deleted(core, directory)
    else:
        tamper_head_ticket_duplicates_the_cp0_ticket(core, directory)
    tampered = file_tree(directory)
    with pytest.raises(core.OwnerError) as error:
        reopen_workflow(core, directory)
    assert error.value.code == "identity_mismatch"
    # Every check that can refuse runs before the recovered record is retained, so a
    # refused open writes nothing: names and bytes are exactly as tampered.
    assert file_tree(directory) == tampered


def test_operands_hash_the_producer_once(monkeypatch):
    from datetime import date

    from deploy_vii.contracts import Fact, Module
    from deploy_workflow.earnings import EarningsDeltaReport

    def fact(fact_id):
        return Fact(
            fact_id=fact_id,
            label=fact_id,
            text="x",
            period="FY2025",
            basis="IFRS",
        )

    producer = Module(
        run_id="run-1",
        issuer_id="issuer-1",
        as_of=date(2025, 12, 31),
        module_id="CP-1",
        facts=tuple(
            fact(f)
            for f in (
                "prior.revenue",
                "current.revenue",
                "metric.revenue",
                "current.ebitda",
            )
        ),
    )
    with_prior = point_data()
    without_prior = {
        **point_data(),
        "measure_id": "ebitda",
        "prior_fact_id": None,
        "current_fact_id": "current.ebitda",
        "companion_fact_ids": (),
    }
    core = api()
    from deploy_workflow.earnings import EarningsDeltaPoint

    report = EarningsDeltaReport(
        producer_sha256=producer.content_hash(),
        prior_period_id="FY2024",
        current_period_id="FY2025",
        prior_basis_id="IFRS",
        current_basis_id="IFRS",
        points=(EarningsDeltaPoint(**with_prior), EarningsDeltaPoint(**without_prior)),
        limitations=(),
    )
    expected = producer.content_hash()
    original = type(producer).content_hash
    hashed = []

    def counting(self):
        if self is producer:
            hashed.append(1)
        return original(self)

    monkeypatch.setattr(type(producer), "content_hash", counting)
    lineages = core._operands(producer, report)

    assert len(hashed) == 1
    references = [
        ref
        for lineage in lineages
        for ref in (
            *(() if lineage.prior is None else (lineage.prior.fact,)),
            lineage.current.fact,
            *lineage.companions,
        )
    ]
    assert len(references) == 4
    assert {ref.producer_sha256 for ref in references} == {expected}
