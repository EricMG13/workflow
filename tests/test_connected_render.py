"""Renderer component checks; actual analytical sessions and browser DOM remain separate.

Fixture review shapes reuse C1's source-workflow component builders over the
independently frozen connected manifest. They are input literals, never renderer
expectations; no mock Execution/View or final Module is inserted.
"""

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack

MANIFEST = json.loads((Path(__file__).parents[1] / "cases/connected/manifest.json").read_text())
LIMIT = MANIFEST["source_limit"]
BANNER = "Source readiness only. Financial analysis and Model publication remain unrun."


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


def _renderer():
    assert importlib.util.find_spec("deploy_workflow.rendering") is not None, (
        "Task3 rendering entrypoint is absent"
    )
    return importlib.import_module("deploy_workflow.rendering")


def test_renderer_entrypoint_is_available():
    """Early RED has no producer fixture dependency; actual implementation is missing."""
    assert callable(_renderer().render_source_slice)


def _case(tmp_path, *, gap=False):
    from deploy_workflow.workflow import SourceWorkflow

    pack = make_pack(gap=gap)
    store_path = tmp_path / "execution"
    workflow = SourceWorkflow.create(store_path, pack)
    observe(workflow, gap=gap)
    assert workflow.submit_review(readiness(pack, gap=gap))["status"] == "valid"
    if not gap:
        observe(workflow)
        assert workflow.submit_review(context(pack))["status"] == "valid"
    receipt_path = tmp_path / "source-slice.json"
    receipt = workflow.write_receipt(receipt_path)
    return store_path, receipt_path, receipt


def _payload(html):
    # Component-level data checks cannot establish browser acceptance.
    raw = html.split('<script id="report-data" type="application/json">', 1)[1].split(
        "</script>", 1
    )[0]
    return json.loads(raw)


@pytest.mark.parametrize("gap", [False, True])
def test_real_store_render_preserves_status_sources_and_metadata(tmp_path, gap):
    directory, receipt_path, receipt = _case(tmp_path, gap=gap)
    store = Execution(directory)
    before = store.read().content_hash()
    destination = tmp_path / "published"
    html_path = _renderer().render_source_slice(directory, receipt_path, destination)
    assert html_path == destination / "report.html"
    html = html_path.read_text()
    assert html.count('id="delivery-scope-banner"') == 1
    assert BANNER in html
    # Component wiring only: default-fragment setup precedes the shipped app's
    # data/bootstrap. Actual bare/explicit URL behavior is checked in native IAB.
    before_data = html.split('<script id="report-data"', 1)[0]
    assert "<script>" in before_data
    view = _payload(html)
    assert view["run"]["run_id"] == ("slice-source-gap" if gap else "slice-source-positive")
    modules = {module["module_id"]: module for module in view["modules"]}
    assert modules["CP-0"]["status_word"] == "With limitations"
    assert modules["CP-1"]["status_word"] == "Not run"
    assert not modules["CP-1"]["facts"] and not modules["CP-1"]["claims"]
    cp0 = {fact["fact_id"]: fact["text"] for fact in modules["CP-0"]["facts"]}
    assert cp0["T8.CP-1.exact_command"] == ("DO NOT RUN" if gap else "Run CP-1")
    assert cp0["T4.CP-1.readiness"] == ("CONDITIONAL" if gap else "READY_WITH_LIMITATIONS")
    financial = next(source for source in view["sources"] if source["source_id"] == "financial")
    if gap:
        assert financial["status"] == "missing" and financial["sha256"] is None
        assert financial["spans"] == []
        assert "Financial statements were not supplied." in modules["CP-0"]["limitations"]
    else:
        assert (
            financial["sha256"]
            == "fc03eecff2e157030c498a66e4de3eacb26f778fff7b449924ad8d18cb0e6a9e"
        )
        assert [span["locator"] for span in financial["spans"]] == ["page:1", "page:2", "page:3"]
        assert "Revenue  120  100" in financial["spans"][0]["text"]
    metadata = json.loads((destination / "render-receipt.json").read_text())
    assert metadata["schema_version"] == "source-slice-render/1"
    assert metadata["html_sha256"] == hashlib.sha256(html_path.read_bytes()).hexdigest()
    assert (
        metadata["source_receipt_sha256"] == hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    )
    assert metadata["snapshot_sha256"] == receipt.snapshot_sha256
    assert metadata["pack_sha256"] == receipt.pack_sha256
    assert metadata["cp0_result_sha256"] == receipt.cp0.result_sha256
    assert metadata["cp1_step_output_sha256"] == (None if gap else receipt.cp1.step_output_sha256)
    assert metadata["cp1_refusal"] == ("not_authorized" if gap else None)
    assert metadata["scope"] == BANNER
    assert (destination / "source-slice.json").read_bytes() == receipt_path.read_bytes()
    assert store.read().content_hash() == before


@pytest.mark.parametrize("variant", ["receipt", "snapshot", "pack", "cp0", "cp1-output"])
def test_forged_or_stale_inputs_do_not_publish(tmp_path, variant):
    directory, receipt_path, receipt = _case(tmp_path)
    store = Execution(directory)
    if variant == "receipt":
        payload = json.loads(receipt_path.read_text())
        payload["cp0"]["result_sha256"] = "a" * 64
        receipt_path.write_text(json.dumps(payload))
    elif variant == "snapshot":
        snapshot = store.read()
        store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
    else:
        digest = {
            "pack": receipt.pack_sha256,
            "cp0": receipt.cp0.result_sha256,
            "cp1-output": receipt.cp1.step_output_sha256,
        }[variant]
        (directory / "blobs" / digest).write_text("forged selected artifact")
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        _renderer().render_source_slice(directory, receipt_path, destination)
    assert not destination.exists()


def test_cross_case_receipt_never_mixes_positive_and_gap(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    positive, _, _ = _case(first)
    _, gap_receipt, _ = _case(second, gap=True)
    destination = tmp_path / "mixed"
    with pytest.raises(ValueError):
        _renderer().render_source_slice(positive, gap_receipt, destination)
    assert not destination.exists()


def test_journal_change_after_real_render_refuses_publication(tmp_path, monkeypatch):
    from deploy_vii import render as core_render

    directory, receipt_path, _ = _case(tmp_path)
    store = Execution(directory)
    original = core_render.render

    def render_then_change(*args, **kwargs):
        html = original(*args, **kwargs)
        snapshot = store.read()
        store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return html

    monkeypatch.setattr(core_render, "render", render_then_change)
    destination = tmp_path / "stale"
    with pytest.raises(ValueError):
        _renderer().render_source_slice(directory, receipt_path, destination)
    assert not destination.exists()


def test_existing_destination_is_preserved(tmp_path):
    directory, receipt_path, _ = _case(tmp_path)
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_text("preserve earlier report")
    with pytest.raises((ValueError, FileExistsError)):
        _renderer().render_source_slice(directory, receipt_path, destination)
    assert marker.read_text() == "preserve earlier report"
    assert not (destination / "report.html").exists()


def test_state_change_during_bundle_staging_does_not_publish(tmp_path, monkeypatch):
    directory, receipt_path, _ = _case(tmp_path)
    store = Execution(directory)
    original = Path.write_bytes

    def write_then_change(path, data):
        result = original(path, data)
        if path.name == "source-slice.json" and path.parent.name.startswith(".source-slice-"):
            snapshot = store.read()
            store._write(snapshot.model_copy(update={"parent": snapshot.content_hash()}))
        return result

    monkeypatch.setattr(Path, "write_bytes", write_then_change)
    destination = tmp_path / "changed-during-staging"
    with pytest.raises(ValueError):
        _renderer().render_source_slice(directory, receipt_path, destination)
    assert not destination.exists()


def test_receipt_byte_change_after_render_refuses_publication(tmp_path, monkeypatch):
    from deploy_vii import render as core_render

    directory, receipt_path, _ = _case(tmp_path)
    original = core_render.render

    def render_then_reformat(*args, **kwargs):
        html = original(*args, **kwargs)
        payload = json.loads(receipt_path.read_text())
        receipt_path.write_text(json.dumps(payload, indent=4) + "\n")
        return html

    monkeypatch.setattr(core_render, "render", render_then_reformat)
    destination = tmp_path / "changed-receipt"
    with pytest.raises(ValueError):
        _renderer().render_source_slice(directory, receipt_path, destination)
    assert not destination.exists()


def test_forged_recorded_call_refuses_even_when_journal_and_heads_match(tmp_path):
    """Catches bypassing producer receipt/audit authentication in the renderer."""
    directory, receipt_path, _ = _case(tmp_path)
    payload = json.loads(receipt_path.read_text())
    original = payload["calls"][0]["body"]
    assert isinstance(original, str) and "Northbridge" in original
    payload["calls"][0]["body"] = original.replace("Northbridge", "Otherbridge", 1)
    receipt_path.write_text(json.dumps(payload))
    destination = tmp_path / "forged-tool-proof"
    with pytest.raises(ValueError):
        _renderer().render_source_slice(directory, receipt_path, destination)
    assert not destination.exists()
