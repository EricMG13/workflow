"""CP-8 run driver: pack assembly, literal submissions and the tool-call sequence.

One closed run (CP-0 then CP-8) over the pinned oracle in `cases/cp8-owner`, driven through the
public `OwnerWorkflow` API only. G2 imports `cp8_closed`; `tests/test_owner_cp8.py` runs it.
Nothing here asserts expected values: the oracle files are read, never derived. Not run in
Stage 2 (deferred to Stage 5; see the report's command list).
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import s1a_runs as base

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/cp8-owner"
PINS = json.loads((ROOT / "cases/PINS.json").read_text())
FILES = ("manifest", "submissions", "expected")
NEW = ("prior_case", "update", "market_update")
SEARCH_QUERY = "recorded"


def oracle() -> dict[str, Any]:
    """The three pinned oracle files; a drifted file fails."""
    out: dict[str, Any] = {}
    for name in FILES:
        path = CASE / f"{name}.json"
        key = path.relative_to(ROOT).as_posix()
        if hashlib.sha256(path.read_bytes()).hexdigest() != PINS[key]:
            raise RuntimeError(f"oracle drift: {key}")
        out[name] = json.loads(path.read_text())
    out["financial"] = json.loads(base.FINANCIAL_MANIFEST.read_text())
    return out


def make_pack(case: str) -> PreparedPack:
    """identity from the hash-checked financial manifest; the other sources from the manifest's
    pages (hash-checked), each with the synthetic-source pack limitation; the run from the case."""
    data = oracle()
    manifest = data["manifest"]
    entry = next(c for c in manifest["cases"] if c["case_id"] == case)
    names = {
        s["source_id"]: s["name"]
        for s in data["expected"]["cases"].get(case, {}).get("pack_sources", [])
    }
    identity = next(s for s in data["financial"]["sources"] if s["source_id"] == "identity")
    sources = []
    for item in entry["pack_sources"]:
        sid = item["source_id"]
        raw = identity if sid == "identity" else manifest["new_sources"][sid]
        digest = hashlib.sha256("\f".join(p["text"] for p in raw["pages"]).encode()).hexdigest()
        if not digest == item["sha256"] == raw["sha256"]:
            raise RuntimeError(f"{sid} page hash drift")
        extra: dict[str, Any] = {"extraction_status": "complete"}
        if sid in NEW:
            extra = {
                "media_type": raw["media_type"],
                "extractor": raw["extractor"],
                "extraction_status": raw["extraction_status"],
                "limitation": raw["pack_limitation"],
            }
        sources.append(
            Source(
                source_id=sid,
                name=names.get(sid, raw["name"]),
                status="ready",
                sha256=digest,
                spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in raw["pages"]),
                **extra,
            )
        )
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(entry["run"])), sources=tuple(sources)
    )


def literal(case: str, name: str, pack: PreparedPack | None = None) -> str:
    """One literal as JSON text: `readiness_review` (CP-0) or `submission` (CP-8, the case's
    entry of submissions.json); the pack hash is bound where the oracle marks it."""
    submissions = oracle()["submissions"]
    document = (
        submissions["readiness_review"][case] if name == "readiness_review" else submissions[case]
    )
    text = json.dumps(document, ensure_ascii=False)
    return text if pack is None else text.replace(base.PACK_PLACEHOLDER, pack.content_hash())


def cp8_closed(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 valid, then CP-8: read every cited page, one search, submit the literal. The returned
    workflow holds the settled run (write its receipt to verify it)."""
    pack = make_pack(case)
    workflow = OwnerWorkflow.create(root / "store", pack)
    review = literal(case, "readiness_review", pack)
    base.read_cited(workflow, review)
    base.submit_valid(workflow, review)
    submission = literal(case, "submission", pack)
    base.read_cited(workflow, submission)
    base.search(workflow, "prior_case", SEARCH_QUERY)
    base.submit_valid(workflow, submission)
    return workflow, pack
