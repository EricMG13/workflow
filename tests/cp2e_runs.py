"""CP-2E run driver: pack assembly, literal submissions, run-time substitutions, tool calls.

One closed two-module run (CP-0 then CP-2E) per case over the oracle in `cases/cp2e-owner`,
driven through the public `OwnerWorkflow` API only. G2 imports `cp2e_closed`;
`tests/test_owner_cp2e.py` imports the stage functions. Nothing here asserts expected values:
the oracle files are read, never derived.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Run, Source, Span
from deploy_vii.live.tools import cited_locators
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "cases" / "cp2e-owner"
FINANCIAL_MANIFEST = ROOT / "cases" / "financial" / "manifest.json"
CASES = ("positive", "gap_no_facility_schedule")
PACK_PLACEHOLDER = (
    "<<PACK_SHA256: PreparedPack.content_hash() of the run's pack, bound at run time>>"
)
FINANCIAL_PIN = "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432"
# The search that backs the step's absence objects (the rule needs some search over some source).
ABSENCE_QUERY = "hedge"


def oracle() -> dict[str, Any]:
    """The three oracle files and the financial manifest; the manifest pin is checked."""
    raw = FINANCIAL_MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FINANCIAL_PIN:
        raise RuntimeError("oracle drift: cases/financial/manifest.json")
    return {
        "submissions": json.loads((CASE_DIR / "submissions.json").read_text(encoding="utf-8")),
        "expected": json.loads((CASE_DIR / "expected.json").read_text(encoding="utf-8")),
        "financial": json.loads(raw),
    }


def make_pack(case: str) -> PreparedPack:
    """The case's pack from its oracle `pack_sources`: pages from the financial manifest, each
    source hash recomputed by the pack rule (U+000C joins the pages) and checked to the oracle."""
    data = oracle()
    expected = data["expected"]["cases"][case]
    by_id = {s["source_id"]: s for s in data["financial"]["sources"]}
    sources = []
    for item in expected["pack_sources"]:
        manifest = by_id[item["source_id"]]
        wanted = item.get("pages")
        spans = tuple(
            Span(locator=p["locator"], text=p["text"])
            for p in manifest["pages"]
            if wanted is None or p["locator"] in wanted
        )
        digest = hashlib.sha256("\f".join(s.text for s in spans).encode()).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError(f"{item['source_id']} page hash drift")
        sources.append(
            Source(
                source_id=item["source_id"],
                name=item["name"],
                status=item["status"],
                sha256=digest,
                spans=spans,
                extraction_status="complete",
            )
        )
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(expected["run"])), sources=tuple(sources)
    )


def literal(case: str, name: str, pack: PreparedPack | None = None) -> str:
    """One literal as JSON text: `readiness_review` is the case's CP-0 literal, `macro_fx` the
    case's step literal. The pack hash is bound where the oracle marks it."""
    submissions = oracle()["submissions"]
    document = (
        submissions["readiness_review"][case] if name == "readiness_review" else submissions[case]
    )
    text = json.dumps(document, ensure_ascii=False)
    return text if pack is None else text.replace(PACK_PLACEHOLDER, pack.content_hash())


def read_cited(
    workflow: OwnerWorkflow, payload: str, *, skip: frozenset[tuple[str, str]] = frozenset()
) -> None:
    """One ok `read_pages` call per page:N the payload cites (the cited-page rule), minus `skip`."""
    pages = sorted(
        (source, int(locator.split(":")[1]))
        for source, locator in cited_locators(payload)
        if re.fullmatch(r"page:\d+", locator) and (source, locator) not in skip
    )
    for source, number in pages:
        call = workflow.invoke(
            "read_pages", {"source_id": source, "first_page": number, "last_page": number}
        )
        if call["status"] != "ok":
            raise RuntimeError(f"read_pages {source} page:{number}: {call['error_code']}")


def search(workflow: OwnerWorkflow, source_id: str, query: str) -> None:
    call = workflow.invoke("search_pack", {"query": query, "source_id": source_id})
    if call["status"] != "ok":
        raise RuntimeError(f"search_pack {source_id}: {call['error_code']}")


def submit_valid(workflow: OwnerWorkflow, payload: str) -> dict[str, Any]:
    outcome = workflow.submit_review(payload)
    if outcome["status"] != "valid":
        raise RuntimeError(f"submission not valid: {outcome['status']} {outcome['issues']}")
    return outcome


def start(case: str, root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    pack = make_pack(case)
    return OwnerWorkflow.create(root / "store", pack), pack


def drive_cp0(workflow: OwnerWorkflow, pack: PreparedPack, case: str) -> None:
    payload = literal(case, "readiness_review", pack)
    read_cited(workflow, payload)
    submit_valid(workflow, payload)


def drive_cp2e(
    workflow: OwnerWorkflow,
    case: str,
    *,
    text: str | None = None,
    skip_reads: frozenset[tuple[str, str]] = frozenset(),
    searched: bool = True,
) -> dict[str, Any]:
    """The literal `macro_fx` (or `text`) after its page reads and, unless `searched` is off, a
    search over the financial source."""
    payload = literal(case, "macro_fx") if text is None else text
    read_cited(workflow, payload, skip=skip_reads)
    if searched:
        search(workflow, "financial", ABSENCE_QUERY)
    return workflow.submit_review(payload)


def cp2e_closed(case: str, root: Path) -> tuple[Path, Path]:
    """One closed run of `case` under `root`: (store, sealed receipt). CP-0, then CP-2E; the
    run has no deterministic module, so nothing is published."""
    workflow, pack = start(case, root)
    drive_cp0(workflow, pack, case)
    outcome = drive_cp2e(workflow, case)
    if outcome["status"] != "valid":
        raise RuntimeError(f"CP-2E not valid: {outcome['issues']}")
    workflow.write_receipt(root / "owner-receipt.json")
    return root / "store", root / "owner-receipt.json"
