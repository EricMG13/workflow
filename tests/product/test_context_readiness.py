"""CP-0 accepts a pack that carries the context source next to a filing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deploy_vii.contracts import Source
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare
from deploy_vii.readiness import ReadinessReview, build_readiness
from deploy_workflow.context import CONTEXT_SOURCE_ID, load_context, preparation_request

CASES = Path(__file__).resolve().parents[2] / "cases" / "context"
FIX_MINIMAL = (CASES / "research-minimal.json").read_bytes()
FILING_TEXT = "Revenue was 100."
CONSUMERS = ("CP-1", "CP-1A", "CP-2", "CP-4", "CP-3", "CP-5", "CP-6")


def make_pack(tmp_path: Path) -> PreparedPack:
    root = tmp_path / "root"
    root.mkdir()
    (root / "context.json").write_bytes(FIX_MINIMAL)
    (root / "filing.txt").write_text(FILING_TEXT, encoding="utf-8")
    request = preparation_request(
        load_context(FIX_MINIMAL),
        run_id="ctx-run-1",
        context_path="context.json",
        sources=(SourceRequest(source_id="filing", path="filing.txt", media_type="text/plain"),),
    )
    return prepare(request, root, tmp_path / "pack")


def cite(source: Source, quote: str) -> dict[str, str]:
    span = next(item for item in source.spans if quote in item.text)
    return {
        "source_id": source.source_id,
        "source_sha256": source.sha256 or "",
        "locator": span.locator,
        "quote": quote,
    }


def review(pack: PreparedPack, *, with_context: bool = True) -> ReadinessReview:
    by_id = {source.source_id: source for source in pack.sources}
    filing = cite(by_id["filing"], FILING_TEXT)
    assessments = [
        {
            "source_id": "filing",
            "document_family": "Synthetic filing",
            "authority": "issuer",
            "entity": "Northbridge Group",
            "period": "FY2025",
            "version_relationship": "Single synthetic filing",
            "fidelity": "verified",
            "citations": [filing],
            "limitations": [],
        }
    ]
    if with_context:
        assessments.append(
            {
                "source_id": CONTEXT_SOURCE_ID,
                "document_family": "Run context file",
                "authority": "unknown",
                "entity": "Northbridge Group",
                "period": None,
                "version_relationship": "Analyst-supplied run settings",
                "fidelity": "verified",
                "citations": [cite(by_id[CONTEXT_SOURCE_ID], "Northbridge Group")],
                "limitations": ["Context states settings, not evidence about the issuer."],
            }
        )
    return ReadinessReview.model_validate_json(
        json.dumps(
            {
                "pack_sha256": pack.content_hash(),
                "objective": "Credit snapshot readiness",
                "reporting_period": "FY2025",
                "issuer_confirmed": True,
                "sources": assessments,
                "consumers": [
                    {
                        "module_id": module_id,
                        "readiness": "READY_WITH_LIMITATIONS",
                        "evidence_demand": "A single revenue observation",
                        "source_ids": ["filing"],
                        "rationale": "The filing states revenue.",
                        "citations": [filing],
                        "limitations": ["One line of evidence only."],
                    }
                    for module_id in CONSUMERS
                ],
                "gaps": [],
                "analysis": [
                    {
                        "claim_id": "read-through",
                        "text": "The filing states revenue.",
                        "citations": [filing],
                        "limitation": "One line of evidence only.",
                    }
                ],
            }
        )
    )


def test_readiness_accepts_context_source(tmp_path: Path) -> None:
    pack = make_pack(tmp_path)
    module = build_readiness(pack, review(pack))
    facts = {fact.fact_id: fact.text for fact in module.facts}
    assert facts["T1.run.issuer"] == "Northbridge Group"
    assert facts["P3.context.family"] == "Run context file"
    assert facts["T3.context.authority"] == "unknown"
    assert json.loads(module.model_dump_json())  # serialises


def test_readiness_refuses_review_without_context_assessment(tmp_path: Path) -> None:
    pack = make_pack(tmp_path)
    with pytest.raises(ValueError, match=r"^Assess every prepared source exactly once$") as excinfo:
        build_readiness(pack, review(pack, with_context=False))
    assert type(excinfo.value) is ValueError
