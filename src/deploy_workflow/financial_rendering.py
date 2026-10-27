"""Read-only delivery of authenticated CP1 financials and a published historical Model."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from deploy_vii import render as core_render
from deploy_vii.contracts import View
from deploy_vii.cp1_render import envelope_view
from deploy_vii.cp1_workflow import read_cp1_envelope, write_cp1_envelope
from deploy_vii.execution import Execution

if TYPE_CHECKING:
    from deploy_workflow.financial_workflow import FinancialSliceReceipt

_MODEL_FILES = frozenset({"model.html", "calculation.json", "receipt.json"})
_POSITIVE_SCOPE = (
    "Historical financial analysis and Model publication only. "
    "Remaining analytical owners and forward projections remain unqualified."
)
_NEGATIVE_SCOPE = (
    "Financial source missing. CP1 financial analysis and Model publication did not run."
)


def _verified_financial_view(
    store: Execution, receipt_path: Path, model_directory: Path | None
) -> tuple[FinancialSliceReceipt, bytes, View, dict[str, bytes]]:
    # Only the producer's public strict schema/verifier authenticates the
    # participant audit, all five stages, promotion and publication. No local
    # replacement schema or private candidate constructor grants that authority.
    from deploy_workflow.financial_workflow import (
        FinancialSliceReceipt,
        verify_financial_slice_receipt,
    )

    raw = receipt_path.read_bytes()
    receipt = FinancialSliceReceipt.model_validate_json(raw)
    verify_financial_slice_receipt(store, receipt, model_directory=model_directory)
    snapshot = store.read()
    if (
        snapshot.content_hash() != receipt.snapshot_sha256
        or store.pack(snapshot).content_hash() != receipt.pack_sha256
        or snapshot.run != receipt.run
    ):
        raise ValueError("stale_financial_slice")
    if set(snapshot.run.requested_modules) != {"CP-1", "CP-MODEL"}:
        raise ValueError("outside_financial_slice")
    heads = {head.module_id: head for head in snapshot.heads}
    publication: dict[str, bytes] = {}
    if receipt.refusal is not None:
        if (
            receipt.refusal != "cp1_not_authorized"
            or receipt.cp1 is not None
            or receipt.model is not None
            or model_directory is not None
            or set(heads) != {"CP-0"}
        ):
            raise ValueError("invalid_financial_gap")
    else:
        if (
            receipt.cp1 is None
            or receipt.model is None
            or model_directory is None
            or set(heads) != {"CP-0", "CP-1", "CP-MODEL"}
            or receipt.cp1.status not in {"accepted", "restricted"}
            or heads["CP-1"].status != receipt.cp1.status
            or heads["CP-1"].result_sha256 != receipt.cp1.result_sha256
            or heads["CP-MODEL"].status not in {"accepted", "restricted"}
            or heads["CP-MODEL"].result_sha256 != receipt.model.result_sha256
            or receipt.model.cp1_result_sha256 != receipt.cp1.result_sha256
            or set(receipt.model.files) != _MODEL_FILES
        ):
            raise ValueError("invalid_financial_publication")
        publication = {name: (model_directory / name).read_bytes() for name in _MODEL_FILES}
        if any(
            hashlib.sha256(raw_file).hexdigest() != receipt.model.files[name]
            for name, raw_file in publication.items()
        ):
            raise ValueError("changed_model_publication")
    view = store.view()
    modules = {module.module_id: module for module in view.modules}
    if view.run != receipt.run:
        raise ValueError("foreign_financial_view")
    for module_id in ("CP-1", "CP-MODEL"):
        shown = modules[module_id]
        if receipt.refusal is not None:
            if (
                shown.status != "unrun"
                or shown.artifact_sha256 is not None
                or shown.facts
                or shown.tables
                or shown.claims
            ):
                raise ValueError("invalid_financial_gap_view")
        elif (
            shown.status != heads[module_id].status
            or shown.artifact_sha256 != heads[module_id].result_sha256
        ):
            raise ValueError("invalid_financial_view")
    if store.read().content_hash() != receipt.snapshot_sha256:
        raise ValueError("stale_financial_slice")
    return receipt, raw, view, publication


def render_financial_slice(
    execution_directory: Path,
    receipt_path: Path,
    model_directory: Path | None,
    destination: Path,
) -> Path:
    """Render the selected run and copy its verified publication into a new destination.

    Trusted setup owns every path and exclusively owns the new destination.
    Authentication is repeated after rendering and before complete staged export;
    no Execution transition or analytical/rendering qualification is performed.
    """
    execution_directory, receipt_path, destination = (
        Path(execution_directory),
        Path(receipt_path),
        Path(destination),
    )
    model_directory = None if model_directory is None else Path(model_directory)
    store = Execution(execution_directory)
    try:
        receipt, raw, view, publication = _verified_financial_view(
            store, receipt_path, model_directory
        )
        if destination.exists():
            raise ValueError("destination_exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".financial-slice-", dir=destination.parent) as temporary:
            stage = Path(temporary)
            files = {"financial-slice.json": raw}
            if receipt.refusal is None:
                # These APIs export/read the genuine promoted head. They only
                # write export files, never the Execution journal or its heads.
                envelope_directory = stage / "cp1"
                write_cp1_envelope(store, envelope_directory)
                envelope = read_cp1_envelope(store, envelope_directory)
                view = envelope_view(view, envelope)
                del envelope
                files.update(
                    ("cp1/" + name, (envelope_directory / name).read_bytes())
                    for name in ("envelope.md", "envelope.json", "complete.json")
                )
                files.update(("model/" + name, body) for name, body in publication.items())
                # The real Model panel links a basename relative to report.html.
                files["calculation.json"] = publication["calculation.json"]
                scope = _POSITIVE_SCOPE
            else:
                scope = _NEGATIVE_SCOPE
            html = core_render.render(view)
            del view
            anchor = '<div id="call-root"></div>'
            if html.count(anchor) != 1:
                raise ValueError("financial_scope_target_missing")
            banner = (
                '<section id="delivery-scope-banner" class="banner" role="note" '
                'data-delivery-scope="historical-financials">' + scope + "</section>"
            )
            files["report.html"] = html.replace(anchor, banner + anchor, 1).encode("utf-8")
            del html
            checked, checked_raw, checked_view, checked_publication = _verified_financial_view(
                store, receipt_path, model_directory
            )
            if checked != receipt or checked_raw != raw or checked_publication != publication:
                raise ValueError("stale_financial_slice")
            del checked, checked_raw, checked_view, checked_publication
            metadata = {
                "schema_version": "cp1-model-slice-render/1",
                "scope": scope,
                "run": receipt.run.model_dump(mode="json"),
                "pack_sha256": receipt.pack_sha256,
                "snapshot_sha256": receipt.snapshot_sha256,
                "financial_receipt_file": "financial-slice.json",
                "financial_receipt_sha256": hashlib.sha256(raw).hexdigest(),
                "cp1_result_sha256": None if receipt.cp1 is None else receipt.cp1.result_sha256,
                "model_result_sha256": None
                if receipt.model is None
                else receipt.model.result_sha256,
                "refusal": receipt.refusal,
                "files": {
                    name: hashlib.sha256(body).hexdigest() for name, body in sorted(files.items())
                },
            }
            files["render-receipt.json"] = (
                json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            ).encode("utf-8")
            del metadata
            for name, body in files.items():
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
            final, final_raw, _, final_publication = _verified_financial_view(
                store, receipt_path, model_directory
            )
            if (
                final != receipt
                or final_raw != raw
                or final_publication != publication
                or destination.exists()
                or any((stage / name).read_bytes() != body for name, body in files.items())
            ):
                raise ValueError("stale_financial_slice")
            os.rename(stage, destination)
        return destination / "report.html"
    except (ValueError, OSError):
        raise ValueError("financial_slice_render_refused") from None
