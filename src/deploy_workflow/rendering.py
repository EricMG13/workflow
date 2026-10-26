"""Authenticate and publish the bounded source-readiness slice using the shipped renderer."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from deploy_vii import render as core_render
from deploy_vii.contracts import View
from deploy_vii.execution import Execution, NotAuthorized, current_inputs

if TYPE_CHECKING:
    from deploy_workflow.workflow import SourceSliceReceipt

SCOPE = "Source readiness only. Financial analysis and Model publication remain unrun."
_DEFAULT_ROUTE = (
    "<script>if (!window.location.hash) {"
    ' window.history.replaceState(null, "", "#evidence"); }</script>'
)
_BANNER = (
    '<section id="delivery-scope-banner" class="banner" role="note" '
    'data-delivery-scope="source-readiness">' + SCOPE + "</section>"
)


def _verified_view(store: Execution, receipt_path: Path) -> tuple[SourceSliceReceipt, bytes, View]:
    # Producer code can land independently of this module; importing this entry
    # point never substitutes a local receipt schema or a mock authorization path.
    from deploy_workflow.workflow import SourceSliceReceipt, verify_source_slice_receipt

    raw = receipt_path.read_bytes()
    receipt = SourceSliceReceipt.model_validate_json(raw)
    verify_source_slice_receipt(store, receipt)
    snapshot = store.read()
    if (
        snapshot.content_hash() != receipt.snapshot_sha256
        or store.pack(snapshot).content_hash() != receipt.pack_sha256
    ):
        raise ValueError("stale_source_slice")
    if snapshot.run != receipt.run:
        raise ValueError("foreign_source_slice")
    # This entry point publishes only the finite readiness/context slice. A
    # broader selected run or settled analyst head needs its own delivery lease.
    if set(snapshot.run.requested_modules) != {"CP-1"} or {h.module_id for h in snapshot.heads} != {
        "CP-0"
    }:
        raise ValueError("outside_source_slice")
    cp0 = store.result(receipt.cp0.result_sha256)
    if cp0.module_id != "CP-0" or cp0.status != receipt.cp0.status:
        raise ValueError("invalid_source_slice")
    cp1_attempts = (attempt for attempt in snapshot.attempts if attempt.module_id == "CP-1")
    if receipt.cp1 is None:
        if receipt.cp1_refusal != "not_authorized" or next(cp1_attempts, None) is not None:
            raise ValueError("invalid_source_gap")
        try:
            current_inputs(snapshot, "CP-1")
        except NotAuthorized:
            pass
        else:
            raise ValueError("invalid_source_gap")
    else:
        consumer = receipt.cp1
        if (
            receipt.cp1_refusal is not None
            or consumer.status != "pending"
            or consumer.selected_cp0_sha256 != cp0.content_hash()
            or consumer.inputs != current_inputs(snapshot, "CP-1")
        ):
            raise ValueError("invalid_source_consumer")
        matches = (attempt for attempt in cp1_attempts if attempt.ticket_id == consumer.ticket_id)
        attempt = next(matches, None)
        if attempt is None or next(matches, None) is not None:
            raise ValueError("invalid_source_consumer")
        if (
            attempt.status != "pending"
            or attempt.inputs != consumer.inputs
            or len(attempt.steps) != 1
            or attempt.steps[0].step_id != "source_context"
            or attempt.steps[0].status != "valid"
            or attempt.steps[0].content_hash() != consumer.step_sha256
            or attempt.steps[0].output_sha256 != consumer.step_output_sha256
        ):
            raise ValueError("invalid_source_consumer")
        store.step_output(consumer.step_output_sha256)  # checked bytes, never a fake CP1 Module
    view = store.view()
    modules = {module.module_id: module for module in view.modules}
    if (
        view.run != receipt.run
        or modules["CP-0"].artifact_sha256 != receipt.cp0.result_sha256
        or modules["CP-1"].status != "unrun"
        or modules["CP-1"].facts
        or modules["CP-1"].claims
        or modules["CP-1"].artifact_sha256 is not None
        or modules["CP-MODEL"].status != "not_in_pathway"
    ):
        raise ValueError("invalid_source_view")
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise ValueError("stale_source_slice")
    return receipt, raw, view


def render_source_slice(execution_directory: Path, receipt_path: Path, destination: Path) -> Path:
    """Publish report.html and identity metadata in a new, exclusive destination.

    All paths are trusted setup. The producer's strict typed verifier owns receipt
    and audit authentication. Publication rechecks that same selected state after
    actual rendering; existing outputs are never overwritten. No workflow is run,
    submitted or promoted by rendering, and no browser acceptance is implied.
    """
    execution_directory, receipt_path, destination = (
        Path(execution_directory),
        Path(receipt_path),
        Path(destination),
    )
    store = Execution(execution_directory)
    try:
        receipt, raw, view = _verified_view(store, receipt_path)
        if destination.exists():
            raise ValueError("destination_exists")
        html = core_render.render(view)
        del view
        anchor = '<div id="call-root"></div>'
        if html.count(anchor) != 1:
            raise ValueError("source_slice_banner_target_missing")
        data_anchor = '<script id="report-data"'
        if html.count(data_anchor) != 1:
            raise ValueError("source_slice_bootstrap_target_missing")
        html = html.replace(anchor, _BANNER + anchor, 1)
        html_bytes = html.replace(data_anchor, _DEFAULT_ROUTE + data_anchor, 1).encode("utf-8")
        del html
        metadata = {
            "schema_version": "source-slice-render/1",
            "scope": SCOPE,
            "run": receipt.run.model_dump(mode="json"),
            "pack_sha256": receipt.pack_sha256,
            "snapshot_sha256": receipt.snapshot_sha256,
            "source_receipt_file": "source-slice.json",
            "source_receipt_sha256": hashlib.sha256(raw).hexdigest(),
            "html_file": "report.html",
            "html_sha256": hashlib.sha256(html_bytes).hexdigest(),
            "cp0_result_sha256": receipt.cp0.result_sha256,
            "cp0_step_output_sha256": receipt.cp0.step_output_sha256,
            "cp1_ticket_id": None if receipt.cp1 is None else receipt.cp1.ticket_id,
            "cp1_step_output_sha256": None
            if receipt.cp1 is None
            else receipt.cp1.step_output_sha256,
            "cp1_refusal": receipt.cp1_refusal,
        }
        checked, checked_raw, checked_view = _verified_view(store, receipt_path)
        if checked != receipt or checked_raw != raw:
            raise ValueError("stale_source_slice")
        del checked, checked_raw, checked_view
        destination.parent.mkdir(parents=True, exist_ok=True)
        # The setup-selected destination has one writer. Stage the complete
        # standalone bundle beside it; no partial report is exposed on refusal.
        with TemporaryDirectory(prefix=".source-slice-", dir=destination.parent) as temporary:
            stage = Path(temporary)
            (stage / "report.html").write_bytes(html_bytes)
            (stage / "source-slice.json").write_bytes(raw)
            (stage / "render-receipt.json").write_text(
                json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                encoding="utf-8",
            )
            final, final_raw, _ = _verified_view(store, receipt_path)
            if final != receipt or final_raw != raw or destination.exists():
                raise ValueError("stale_source_slice")
            os.rename(stage, destination)
        return destination / "report.html"
    except (ValueError, OSError):
        raise ValueError("source_slice_render_refused") from None
