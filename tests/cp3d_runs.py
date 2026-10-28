"""CP-3D run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed two-module run (CP-0, then CP-3D) over the pinned oracle in `cases/cp3d-owner`, driven
through the public `OwnerWorkflow` API only. G2 imports `cp3d_closed`; `tests/test_owner_cp3d.py`
imports the stage functions to fork a run after CP-0. Nothing here asserts expected values: the
oracle files are read, never derived. The plan is CP-0, CP-3D (no CP-1 promotion).
"""

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "cases/cp3d-owner"
CASES = ("positive", "gap_no_recovery", "gap_no_market")
# The market source of the sheet no other preparation may revise: the two page bytes are checked
# against the manifest's pinned source hash, not a file.
SOURCE_ID = "market"
SEARCH_QUERY = "Northbridge"


def _s1a() -> Any:
    return importlib.import_module("s1a_runs")


def oracle() -> dict[str, Any]:
    """The three oracle files of the module (their pins are checked by `test_method_cp3d`)."""
    return {
        name: json.loads((ORACLE / f"{name}.json").read_text(encoding="utf-8"))
        for name in ("manifest", "submissions", "expected")
    }


def make_pack(case: str) -> PreparedPack:
    """identity and financial from the hash-checked S1 pack, market from the pinned sheet (absent
    from `gap_no_market`), the run of the case; each source is checked against the manifest."""
    manifest = oracle()["manifest"]
    entry = next(c for c in manifest["cases"] if c["case_id"] == case)
    held = {s.source_id: s for s in _s1a().make_pack("positive").sources}
    market = manifest["market_source_pin"]
    joined = "\f".join(p["text"] for p in market["pages"]).encode()
    if hashlib.sha256(joined).hexdigest() != market["source_sha256"]:
        raise RuntimeError("market source page drift")
    sources = []
    for item in entry["pack_sources"]:
        if item["source_id"] == SOURCE_ID:
            source = Source(
                source_id=SOURCE_ID,
                name=item["name"],
                status="ready",
                sha256=market["source_sha256"],
                media_type="text/plain",
                spans=tuple(Span(**page) for page in market["pages"]),
                extraction_status="complete",
            )
        else:
            source = held[item["source_id"]]
        if (source.source_id, source.name, source.sha256) != (
            item["source_id"],
            item["name"],
            item["sha256"],
        ):
            raise RuntimeError(f"{item['source_id']} source drift")
        sources.append(source)
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(entry["run"])), sources=tuple(sources)
    )


def cp0_literal(case: str, pack: PreparedPack) -> str:
    """The case's CP-0 readiness review with the pack hash bound where the oracle marks it."""
    review = oracle()["submissions"]["readiness_review"][case]
    text = json.dumps(review, ensure_ascii=False)
    return text.replace(_s1a().PACK_PLACEHOLDER, pack.content_hash())


def literal(case: str) -> str:
    """The case's literal `market_implied` submission as JSON text (nothing to bind)."""
    return json.dumps(oracle()["submissions"][case], ensure_ascii=False)


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    return OwnerWorkflow.create(root / "store", pack, specs=OWNER_SPECS), pack


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    """CP-0 to its settlement: one read per cited page, then the literal review."""
    payload = cp0_literal(case, pack)
    runs = _s1a()
    runs.read_cited(workflow, payload)
    runs.submit_valid(workflow, payload)


def drive_cp3d(
    workflow: OwnerWorkflow, case: str, *, text: str | None = None, search: bool = True
) -> dict[str, Any]:
    """The tool-call sequence the oracle requires, then the submit: one ok `read_pages` per
    cited page, one ok `search_pack` (over the market source, else the financial one) when the
    literal holds an absence object, and no `read_inputs` (the step has none)."""
    payload = literal(case) if text is None else text
    runs = _s1a()
    runs.read_cited(workflow, payload)
    if search:
        held = {s.source_id for s in make_pack(case).sources}
        runs.search(workflow, SOURCE_ID if SOURCE_ID in held else "financial", SEARCH_QUERY)
    outcome: dict[str, Any] = workflow.submit_review(payload)
    return outcome


def after_cp0(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 settled and CP-3D begun and untouched (no call yet, so it can be cloned)."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case)
    return workflow, pack


def cp3d_closed(case: str, root: Path) -> tuple[Path, Path]:
    """One closed run of `case` under `root`: (store, sealed receipt)."""
    workflow, _ = after_cp0(case, root)
    outcome = drive_cp3d(workflow, case)
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-3D not valid: {outcome['issues']}")
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json"


def head_of_module(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)
