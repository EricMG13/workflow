"""Connected slice component cases; these fixtures are not the analytical participant.

Independent expectations come from connected/manifest.json, frozen before the bridge.
The actual retained host run must be separately performed using real observed tool bodies.
"""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.cp0_workflow import submit_cp0_review
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.host import SourceSession

MANIFEST = json.loads((Path(__file__).parents[1] / "cases/connected/manifest.json").read_text())
LIMIT = MANIFEST["source_limit"]


def make_pack(gap=False):
    run = dict(MANIFEST["run"])
    if gap:
        run["run_id"] = "slice-source-gap"
    sources = []
    for item in MANIFEST["sources"]:
        missing = gap and item["source_id"] == "financial"
        spans = (
            ()
            if missing
            else tuple(Span(locator=p["locator"], text=p["text"]) for p in item["pages"])
        )
        if not missing:
            assert (
                hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest()
                == item["sha256"]
            )
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["name"],
                status="missing" if missing else "ready",
                sha256=None if missing else item["sha256"],
                spans=spans,
                extraction_status="blocked" if missing else "complete",
                limitation="Financial statements were not supplied."
                if missing
                else LIMIT
                if item["source_id"] == "financial"
                else None,
            )
        )
    return PreparedPack(run=Run.model_validate_json(json.dumps(run)), sources=tuple(sources))


def cite(source, locator, quote):
    item = next(s for s in MANIFEST["sources"] if s["source_id"] == source)
    return {
        "source_id": source,
        "source_sha256": item["sha256"],
        "locator": locator,
        "quote": quote,
    }


IDENTITY_CITE = cite(
    "identity", "page:1", "Northbridge Synthetic Group is the issuer and consolidated group."
)
FINANCIAL_CITES = [
    cite("financial", "page:1", "Currency: USD; amounts in millions."),
    cite("financial", "page:2", "Total assets  110  95"),
    cite("financial", "page:3", "As of January 10, 2026, no subsequent events are reported."),
]


def readiness(pack, gap=False):
    return json.dumps(
        {
            "pack_sha256": pack.content_hash(),
            "objective": MANIFEST["positive_expectations"]["CP-0"]["review_objective"],
            "reporting_period": "FY2025/FY2024",
            "issuer_confirmed": True,
            "sources": [
                {
                    "source_id": "identity",
                    "document_family": "Issuer identity note",
                    "authority": "issuer",
                    "entity": "Northbridge Synthetic Group",
                    "period": "Published January 10, 2026",
                    "version_relationship": "Identity evidence accompanying the annual statements",
                    "fidelity": "verified",
                    "citations": [IDENTITY_CITE],
                    "limitations": [
                        "No borrower, guarantor or restricted-group perimeter established."
                    ],
                },
                {
                    "source_id": "financial",
                    "document_family": "Annual financial statements",
                    "authority": "unknown" if gap else "issuer",
                    "entity": None if gap else "Northbridge Synthetic Group",
                    "period": None if gap else "FY2025/FY2024",
                    "version_relationship": "Not supplied"
                    if gap
                    else "Issuer-prepared unaudited annual report",
                    "fidelity": "blocked" if gap else "verified",
                    "citations": [] if gap else FINANCIAL_CITES,
                    "limitations": ["Financial statements were not supplied."] if gap else [LIMIT],
                },
            ],
            "consumers": [
                {
                    "module_id": "CP-1",
                    "readiness": "CONDITIONAL" if gap else "READY_WITH_LIMITATIONS",
                    "evidence_demand": MANIFEST["positive_expectations"]["CP-0"]["evidence_demand"],
                    "source_ids": ["identity"] if gap else ["identity", "financial"],
                    "rationale": "The annual financial statements are missing."
                    if gap
                    else "The entire selected CP-1 FY2025/FY2024 canonical-foundation owner method can run "
                    "with absent financial notes, debt and facility terms, maturities, covenants, "
                    "segments, KPIs, add-backs, narrative drivers, quarterly data and borrower, "
                    "guarantor and restricted perimeters explicitly recorded as limitations. "
                    "This asserts no quarterly, Model, legal or specialist sufficiency.",
                    "citations": [IDENTITY_CITE] if gap else [IDENTITY_CITE, *FINANCIAL_CITES],
                    "missing_source": "Annual financial statements" if gap else None,
                    "limitations": ["Financial statements were not supplied."] if gap else [LIMIT],
                }
            ],
            "gaps": [{"gap_id": "missing-financial", **MANIFEST["gap_case"]["explicit_gap"]}]
            if gap
            else [],
            "analysis": [
                {
                    "claim_id": "source-readthrough",
                    "text": "Identity evidence is usable; annual financial evidence is missing."
                    if gap
                    else "Located annual statements support the selected historical foundation with limitations.",
                    "citations": [IDENTITY_CITE] if gap else [IDENTITY_CITE, *FINANCIAL_CITES],
                    "limitation": "Financial statements were not supplied." if gap else LIMIT,
                }
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def context(pack):
    scopes = [
        {
            "scope_id": "fy-" + year,
            "entity_id": "issuer",
            "period_label": "FY" + year,
            "period_kind": "historical_duration",
            "start_date": year + "-01-01",
            "end_date": year + "-12-31",
            "currency": "USD",
            "unit": "MILLIONS",
            "entity_perimeter": "consolidated group",
            "accounting_basis": "IFRS",
            "citations": [FINANCIAL_CITES[0]],
            "limitations": [LIMIT],
        }
        for year in ("2025", "2024")
    ]
    return json.dumps(
        {
            "pack_sha256": pack.content_hash(),
            "entities": [
                {
                    "entity_id": "issuer",
                    "name": "Northbridge Synthetic Group",
                    "entity_type": "group",
                    "roles": ["issuer"],
                    "fiscal_year_end": "December 31",
                    "citations": [IDENTITY_CITE],
                    "limitations": [
                        "Borrower, guarantor and restricted-group perimeters are not established."
                    ],
                }
            ],
            "sources": [
                {
                    "source_id": "identity",
                    "classification": "nonfinancial",
                    "document_type": "Issuer identity note",
                    "published_on": "2026-01-10",
                    "evidence_class": "internal",
                    "evidence_rationale": "Issuer identity note; no external assurance claimed.",
                    "analytical_use": "Issuer identity only.",
                    "citations": [IDENTITY_CITE],
                    "event_scan": "unassessed",
                    "event_scan_explanation": "Identity note is not an event inventory.",
                    "limitations": ["No reporting scope supplied by the identity note."],
                },
                {
                    "source_id": "financial",
                    "classification": "financial",
                    "document_type": "Issuer-prepared unaudited annual financial statements",
                    "published_on": "2026-01-10",
                    "evidence_class": "unaudited_without_auditor",
                    "evidence_rationale": "Issuer-prepared unaudited statements; no auditor report supplied.",
                    "analytical_use": "Restricted historical FY foundation only.",
                    "citations": FINANCIAL_CITES,
                    "scopes": scopes,
                    "event_scan": "no_events_identified",
                    "event_scan_citations": [FINANCIAL_CITES[2]],
                    "event_scan_explanation": "No events reported within this dated supplied report only.",
                    "limitations": [LIMIT],
                },
            ],
            "events": [],
            "limitations": [LIMIT],
        },
        separators=(",", ":"),
    )


def api():
    assert importlib.util.find_spec("deploy_workflow.workflow") is not None, (
        "Task3 workflow is absent"
    )
    return __import__("deploy_workflow.workflow", fromlist=["SourceWorkflow"])


def observe(workflow, gap=False, omit_financial=False):
    assert (
        workflow.invoke("search_pack", {"query": "Northbridge", "source_id": "identity"})["status"]
        == "ok"
    )
    assert (
        workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})[
            "status"
        ]
        == "ok"
    )
    if not gap:
        assert (
            workflow.invoke(
                "search_pack", {"query": "subsequent events", "source_id": "financial"}
            )["status"]
            == "ok"
        )
        result = workflow.invoke(
            "read_pages",
            {"source_id": "financial", "first_page": 1, "last_page": 2 if omit_financial else 3},
        )
        assert result["status"] == "ok"
        assert "Revenue  120  100" in result["body"]


def test_real_cp0_review_extra_input_is_accepted_by_cp1_source_factory(tmp_path):
    """Catches incompatible exact-input check rejecting CP0's canonical review binding."""
    pack = make_pack()
    store = Execution.create(tmp_path / "execution", pack)
    cp0 = store.begin("CP-0")
    finished = submit_cp0_review(store, cp0.ticket_id, readiness(pack))
    assert finished.status == "finished" and not finished.issues
    result = store.result(finished.result_sha256)
    assert result.status == "restricted"
    assert [i.input_id for i in result.inputs] == ["prepared-pack", "readiness-review"]
    cp1 = store.begin("CP-1")
    SourceSession.from_execution(store, cp1.ticket_id, "source_context")


def test_real_positive_slice_retains_cp0_settlement_and_cp1_consumer(tmp_path):
    module = api()
    pack = make_pack()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", pack)
    observe(workflow)
    assert workflow.submit_review(readiness(pack))["status"] == "valid"
    observe(workflow)
    assert workflow.submit_review(context(pack))["status"] == "valid"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert receipt.schema_version == "source-slice-receipt/1"
    assert receipt.cp0.status == "restricted"
    assert receipt.cp0.step_output_sha256 != receipt.cp0.result_sha256
    assert receipt.cp1 is not None and receipt.cp1.status == "pending"
    assert receipt.cp1.output_status == "restricted"
    assert receipt.cp1.selected_cp0_sha256 == receipt.cp0.result_sha256
    assert receipt.cp1.inputs[1].sha256 == receipt.cp0.result_sha256
    assert receipt.cp1.inputs[1].status == "restricted"
    assert receipt.cp1_refusal is None
    snapshot = Execution(tmp_path / "execution").read()
    assert [h.module_id for h in snapshot.heads] == ["CP-0"]
    assert snapshot.attempts[-1].steps[0].status == "valid"
    assert len({c.binding.snapshot_sha256 for c in receipt.calls}) == 2
    assert receipt.snapshot_sha256 not in {c.binding.snapshot_sha256 for c in receipt.calls}
    module.verify_source_slice_receipt(Execution(tmp_path / "execution"), receipt)


def test_gap_uses_real_not_authorized_without_cp1_ticket(tmp_path):
    module = api()
    pack = make_pack(gap=True)
    workflow = module.SourceWorkflow.create(tmp_path / "execution", pack)
    observe(workflow, gap=True)
    assert workflow.submit_review(readiness(pack, gap=True))["status"] == "valid"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert receipt.cp0.status == "restricted"
    assert receipt.cp1 is None and receipt.cp1_refusal == "not_authorized"
    assert [a.module_id for a in Execution(tmp_path / "execution").read().attempts] == ["CP-0"]
    module.verify_source_slice_receipt(Execution(tmp_path / "execution"), receipt)


def test_unread_review_refuses_before_any_journal_submission(tmp_path):
    module = api()
    pack = make_pack()
    directory = tmp_path / "execution"
    workflow = module.SourceWorkflow.create(directory, pack)
    observe(workflow, omit_financial=True)
    before = Execution(directory).read()
    result = workflow.submit_review(readiness(pack))
    assert result["status"] == "refused" and result["error_code"] == "evidence_refused"
    after = Execution(directory).read()
    assert after.content_hash() == before.content_hash()
    assert not after.attempts[0].steps and not after.heads
    assert (
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 3, "last_page": 3})[
            "status"
        ]
        == "ok"
    )
    assert workflow.submit_review(readiness(pack))["status"] == "valid"


def test_transport_refuses_path_and_code_arguments(tmp_path):
    from io import StringIO

    module = api()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", make_pack())
    requests = StringIO(
        "\n".join(
            json.dumps(r)
            for r in [
                {"operation": "write_receipt", "destination": str(tmp_path / "escape.json")},
                {"operation": "shell", "command": "cat /etc/passwd"},
                {
                    "operation": "invoke",
                    "tool": "read_pages",
                    "arguments": {"source_id": "identity", "first_page": 1, "last_page": 1},
                },
            ]
        )
        + "\n"
    )
    output = StringIO()
    module.serve_json_lines(
        workflow,
        requests,
        output,
        destination=tmp_path / "receipt.json",
        participant="component-test",
    )
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [r["status"] for r in replies] == ["refused", "refused", "ok"]
    assert not (tmp_path / "escape.json").exists()


@pytest.mark.parametrize("coordinate", ["payload", "pack", "calls"])
def test_wrong_submission_binding_refuses_before_journal(tmp_path, monkeypatch, coordinate):
    module = api()
    pack = make_pack()
    directory = tmp_path / "execution"
    workflow = module.SourceWorkflow.create(directory, pack)
    observe(workflow)
    original = workflow._session.bind_submission

    def wrong(payload):
        value = original(payload)
        if coordinate == "payload":
            value["payload_sha256"] = "0" * 64
        elif coordinate == "pack":
            value["binding"]["pack_sha256"] = "0" * 64
        else:
            value["successful_call_ids"] = ["invented-call"]
        return value

    monkeypatch.setattr(workflow._session, "bind_submission", wrong)
    before = Execution(directory).read().content_hash()
    with pytest.raises(module.WorkflowError, match="identity_mismatch"):
        workflow.submit_review(readiness(pack))
    assert Execution(directory).read().content_hash() == before


@pytest.mark.parametrize(
    "coordinate", ["cp0_result", "cp1_output", "stale_snapshot", "foreign_run"]
)
def test_receipt_verifier_refuses_forged_or_stale_references(tmp_path, coordinate):
    module = api()
    pack = make_pack()
    directory = tmp_path / "execution"
    workflow = module.SourceWorkflow.create(directory, pack)
    observe(workflow)
    workflow.submit_review(readiness(pack))
    observe(workflow)
    workflow.submit_review(context(pack))
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = Execution(directory)
    if coordinate in ("cp0_result", "cp1_output"):
        digest = (
            receipt.cp0.result_sha256
            if coordinate == "cp0_result"
            else receipt.cp1.step_output_sha256
        )
        (directory / "blobs" / digest).write_text('{"forged":true}')
    elif coordinate == "stale_snapshot":
        store._write(store.read().model_copy(update={"parent": "0" * 64}))
    else:
        receipt = receipt.model_copy(
            update={"run": receipt.run.model_copy(update={"run_id": "foreign"})}
        )
    with pytest.raises(module.WorkflowError):
        module.verify_source_slice_receipt(store, receipt)
    if coordinate != "foreign_run":
        with pytest.raises((module.WorkflowError, ValueError)):
            workflow.write_receipt(tmp_path / "must-not-publish.json")
        assert not (tmp_path / "must-not-publish.json").exists()


def test_context_absence_claim_needs_its_own_successful_search(tmp_path):
    module = api()
    pack = make_pack()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", pack)
    observe(workflow)
    workflow.submit_review(readiness(pack))
    workflow.invoke("search_pack", {"query": "Northbridge", "source_id": "identity"})
    workflow.invoke("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1})
    workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 3})
    before = Execution(tmp_path / "execution").read().content_hash()
    refused = workflow.submit_review(context(pack))
    assert refused["status"] == "refused" and refused["error_code"] == "evidence_refused"
    assert Execution(tmp_path / "execution").read().content_hash() == before
    assert not Execution(tmp_path / "execution").read().attempts[-1].steps
    workflow.invoke("search_pack", {"query": "subsequent events", "source_id": "financial"})
    assert workflow.submit_review(context(pack))["status"] == "valid"


def test_caller_built_accepted_module_cannot_replace_review(tmp_path):
    module = api()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", make_pack())
    observe(workflow)
    result = workflow.submit_review('{"module_id":"CP-0","status":"accepted"}')
    assert result["status"] == "invalid"
    snapshot = Execution(tmp_path / "execution").read()
    assert not snapshot.heads
    assert len(snapshot.attempts) == 1 and snapshot.attempts[0].status == "finished"
    with pytest.raises(module.WorkflowError):
        workflow.write_receipt(tmp_path / "fake.json")
    assert not (tmp_path / "fake.json").exists()


def test_step_budget_stops_real_invocations_at_sixteen(tmp_path):
    module = api()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", make_pack())
    for _ in range(16):
        result = workflow.invoke("search_pack", {"query": "Northbridge", "source_id": "identity"})
        assert result["status"] == "ok"
    with pytest.raises(module.WorkflowError, match="not_permitted"):
        workflow.invoke("search_pack", {"query": "Northbridge", "source_id": "identity"})


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "omitted_steps",
        "changed_hash",
        "reordered",
        "duplicate",
        "unknown",
        "wrong_status",
    ],
)
def test_real_cp0_provenance_cannot_be_dropped_or_forged(tmp_path, defect):
    from deploy_vii.contracts import Input
    from deploy_workflow.tools.source import SourceError

    pack = make_pack()
    store = Execution.create(tmp_path / "execution", pack)
    cp0 = store.begin("CP-0")
    completed = submit_cp0_review(store, cp0.ticket_id, readiness(pack))
    result = store.result(completed.result_sha256)
    inputs = result.inputs
    if defect in ("missing", "omitted_steps"):
        inputs = inputs[:1]
    elif defect == "changed_hash":
        inputs = (inputs[0], inputs[1].model_copy(update={"sha256": "0" * 64}))
    elif defect == "reordered":
        inputs = tuple(reversed(inputs))
    elif defect == "duplicate":
        inputs = (*inputs, inputs[-1])
    elif defect == "unknown":
        inputs = (*inputs, Input(input_id="unknown-provenance", sha256="0" * 64))
    else:
        inputs = (inputs[0], inputs[1].model_copy(update={"status": "restricted"}))
    forged = result.model_copy(update={"inputs": inputs})
    digest = store._store(forged.model_dump_json())
    snapshot = store.read()
    head = snapshot.heads[0].model_copy(update={"result_sha256": digest, "inputs": inputs})
    completed = completed.model_copy(update={"result_sha256": digest})
    if defect == "omitted_steps":
        completed = completed.model_copy(update={"steps": ()})
    store._write(snapshot.model_copy(update={"heads": (head,), "attempts": (completed,)}))
    cp1 = store.begin("CP-1")
    with pytest.raises(SourceError, match="identity_mismatch"):
        SourceSession.from_execution(store, cp1.ticket_id, "source_context")


def test_audit_failure_does_not_allow_more_than_sixteen_real_tool_attempts(tmp_path, monkeypatch):
    module = api()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", make_pack())
    calls = []
    invoke = workflow._session.invoke

    def counted(*args):
        calls.append(args)
        return invoke(*args)

    monkeypatch.setattr(workflow._session, "invoke", counted)

    def disk_failure(*args):
        raise OSError("Synthetic audit disk failure")

    monkeypatch.setattr(module, "_put", disk_failure)
    for _ in range(17):
        try:
            workflow.invoke("search_pack", {"query": "Northbridge", "source_id": "identity"})
        except (OSError, module.WorkflowError):
            pass
    assert len(calls) <= 16


def test_invalid_context_reports_actual_repair_issues(tmp_path):
    module = api()
    pack = make_pack()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", pack)
    observe(workflow)
    workflow.submit_review(readiness(pack))
    observe(workflow)
    wrong = json.loads(context(pack))
    wrong["pack_sha256"] = "0" * 64
    outcome = workflow.submit_review(json.dumps(wrong))
    assert outcome["status"] == "invalid" and outcome["issue_count"] > 0
    attempt = Execution(tmp_path / "execution").read().attempts[-1]
    assert attempt.status == "pending" and attempt.step_repairs[-1].issues


def test_refused_review_has_no_validated_canonical_review_hash(tmp_path):
    module = api()
    pack = make_pack()
    workflow = module.SourceWorkflow.create(tmp_path / "execution", pack)
    observe(workflow, omit_financial=True)
    assert workflow.submit_review(readiness(pack))["status"] == "refused"
    workflow.invoke("read_pages", {"source_id": "financial", "first_page": 3, "last_page": 3})
    assert workflow.submit_review(readiness(pack))["status"] == "valid"
    observe(workflow)
    assert workflow.submit_review(context(pack))["status"] == "valid"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert receipt.submissions[0].disposition == "refused"
    assert receipt.submissions[0].canonical_review_sha256 is None


@pytest.mark.parametrize("kind", ["calls", "payloads", "bindings", "seal"])
def test_receipt_verifier_authenticates_audit_bytes_and_seal(tmp_path, kind):
    module = api()
    pack = make_pack()
    directory = tmp_path / "execution"
    workflow = module.SourceWorkflow.create(directory, pack)
    observe(workflow)
    workflow.submit_review(readiness(pack))
    observe(workflow)
    workflow.submit_review(context(pack))
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    if kind == "seal":
        file = directory / "source-slice-audit" / "receipt.sha256"
    else:
        digest = (
            receipt.calls[0].content_hash()
            if kind == "calls"
            else receipt.submissions[0].payload_sha256
            if kind == "payloads"
            else receipt.submissions[0].binding_sha256
        )
        file = directory / "source-slice-audit" / kind / digest
    file.write_text("tampered")
    with pytest.raises(module.WorkflowError):
        module.verify_source_slice_receipt(Execution(directory), receipt)


def test_receipt_mutation_cannot_pass_the_fixed_execution_seal(tmp_path):
    module = api()
    pack = make_pack(gap=True)
    directory = tmp_path / "execution"
    workflow = module.SourceWorkflow.create(directory, pack)
    observe(workflow, gap=True)
    workflow.submit_review(readiness(pack, gap=True))
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    forged = receipt.model_copy(update={"participant": "forged-participant"})
    with pytest.raises(module.WorkflowError, match="identity_mismatch"):
        module.verify_source_slice_receipt(Execution(directory), forged)


def test_missing_recorded_cp0_post_submit_snapshot_refuses_receipt(tmp_path):
    module = api()
    pack = make_pack()
    directory = tmp_path / "execution"
    workflow = module.SourceWorkflow.create(directory, pack)
    observe(workflow)
    workflow.submit_review(readiness(pack))
    observe(workflow)
    workflow.submit_review(context(pack))
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    after = receipt.submissions[0].snapshot_after_sha256
    assert after != receipt.snapshot_sha256
    assert after not in {c.binding.snapshot_sha256 for c in receipt.calls}
    (directory / "snapshots" / (after + ".json")).unlink()
    with pytest.raises(module.WorkflowError, match="identity_mismatch"):
        module.verify_source_slice_receipt(Execution(directory), receipt)
