"""Phase 5 Task 1: draft legal authority in CP-0, admitted only for a draft context (B7), and the
`context` source never carries authority (B17 item 6).

Packs and reviews come from the frozen oracle `cases/context-attachments-owner` (the builder reads
its manifest and submissions; nothing here derives an expected value). Expected lines are the
oracle's `expected.json#texts`, or the Task 1 brief's own lines for cases the oracle leaves out.
"""

import copy
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from deploy_vii import readiness
from deploy_vii.business_context import SourceUse
from deploy_vii.contracts import Run, Source, Span
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_vii.readiness import ReadinessReview, build_readiness, validate_review

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases/context-attachments-owner"
MANIFEST = json.loads((CASE / "manifest.json").read_text())
SUBMISSIONS = json.loads((CASE / "submissions.json").read_text())
EXPECTED = json.loads((CASE / "expected.json").read_text())
PAGES: dict[str, list[dict[str, str]]] = importlib.import_module("test_method_cp4").PAGES
PLACEHOLDER = SUBMISSIONS["cases"]["draft-ok"]["cp0_review"]["pack_sha256"]
WRONG_CONTEXT = EXPECTED["texts"]["draft_wrong_context"]
NEEDS_DRAFT = "Draft authority needs a context that declares draft legal documents: legal-draft"


def _context_source(path: str, expected_sha: str) -> Source:
    raw = (ROOT / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_sha
    request = SourceRequest(source_id="context", path=path, media_type="text/plain")
    return prepare_source(request, raw)


def _source(item: dict[str, Any]) -> Source:
    if item["source_id"] == "context":
        return _context_source(item["path"], item["sha256"])
    if item["source_id"] == "legal-draft":
        text = (CASE / "legal-draft.txt").read_text()
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == item["sha256"]
        pages = [
            {"locator": f"page:{n}", "text": part} for n, part in enumerate(text.split("\f"), 1)
        ]
    else:
        pages = PAGES[item["sha256"]]
    return Source(
        source_id=item["source_id"],
        name=item["name"],
        status=item["status"],
        sha256=item["sha256"],
        spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in pages),
        extraction_status="complete",
        limitation=item["limitation"],
    )


def make_pack(case_id: str, *, context: str | None = None) -> PreparedPack:
    """The oracle's pack for `case_id`; `context` swaps in another oracle context file."""
    entry = next(c for c in MANIFEST["cases"] if c["case_id"] == case_id)
    items = copy.deepcopy(entry["pack_sources"])
    if context is not None:
        item = next(i for i in items if i["source_id"] == "context")
        item["path"] = f"cases/context-attachments-owner/{context}.json"
        item["sha256"] = MANIFEST["contexts"][context]["sha256"]
    return PreparedPack(
        run=Run.model_validate_json(json.dumps(entry["run"])),
        sources=tuple(_source(i) for i in items),
    )


def make_review(case_id: str, pack: PreparedPack) -> ReadinessReview:
    document = copy.deepcopy(SUBMISSIONS["cases"][case_id]["cp0_review"])
    assert document["pack_sha256"] == PLACEHOLDER
    document["pack_sha256"] = pack.content_hash()
    return ReadinessReview.model_validate_json(json.dumps(document))


def reassess(review: ReadinessReview, source_id: str, authority: str) -> ReadinessReview:
    document = json.loads(review.model_dump_json())
    for item in document["sources"]:
        if item["source_id"] == source_id:
            item["authority"] = authority
    return ReadinessReview.model_validate_json(json.dumps(document))


def issues_of(case_id: str, *, context: str | None = None) -> tuple[str, ...]:
    pack = make_pack(case_id, context=context)
    return validate_review(pack, make_review(case_id, pack))


# --- (a)-(d): the draft rule ----------------------------------------------------------------


def test_draft_ok_validates() -> None:
    assert issues_of("draft-ok") == ()


def test_draft_cited_other_and_uncited_validate() -> None:
    assert issues_of("draft-cited-other") == ()
    assert issues_of("draft-uncited") == ()


def test_draft_with_an_executed_context_is_refused() -> None:
    assert issues_of("draft-wrong-context") == (NEEDS_DRAFT,)
    assert NEEDS_DRAFT == WRONG_CONTEXT.format(source_id="legal-draft")
    # the same review against the executed context, not just the oracle's own pairing (the swapped
    # file also changes the context source's hash, so other lines may accompany the refusal)
    assert NEEDS_DRAFT in issues_of("draft-ok", context="context-executed")


def test_draft_without_a_context_source_is_refused() -> None:
    assert issues_of("draft-wrong-context-no-context") == (NEEDS_DRAFT,)


def test_draft_with_an_invalid_context_is_refused_not_raised() -> None:
    pack = make_pack("draft-ok", context="context-mismatch")
    issues = validate_review(pack, make_review("draft-ok", pack))
    problem = EXPECTED["cases"]["mismatch"]["P"]["issues"][0].removeprefix(
        EXPECTED["texts"]["context_refused_prefix"]
    )
    assert f"Draft authority refused, context invalid: {problem}" in issues
    assert not any(NEEDS_DRAFT in line for line in issues)


# --- (e): no draft assessment, no context read -----------------------------------------------


def test_a_review_without_draft_never_reads_the_context(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_: object, **__: object) -> None:
        raise AssertionError("context_facts must not be called")

    monkeypatch.setattr("deploy_workflow.context.context_facts", boom)
    for case_id in ("none-declared", "abs-gap-ok", "legal-exec-missing-gap"):
        assert issues_of(case_id) == (), case_id


# --- (f), (g): T3 text and the unchanged enum ------------------------------------------------


def test_t3_authority_fact_text_is_draft() -> None:
    pack = make_pack("draft-ok")
    module = build_readiness(pack, make_review("draft-ok", pack))
    texts = [f.text for f in module.facts if f.fact_id == "T3.legal-draft.authority"]
    assert texts == ["draft"]


def test_cp1a_source_class_still_refuses_draft() -> None:
    fields: dict[str, Any] = {
        "source_id": "x",
        "quality": "High",
        "period": None,
        "entity_covered": "e",
        "data_supplied": "d",
        "use": "u",
        "citations": [],
        "limitation": None,
    }
    with pytest.raises(ValidationError):
        SourceUse.model_validate_json(json.dumps({**fields, "source_class": "draft"}))
    assert "draft" not in readiness.Authority.__args__  # type: ignore[attr-defined]
    SourceUse.model_validate_json(json.dumps({**fields, "source_class": "issuer"}))


# --- (h): the context source never carries authority ----------------------------------------


@pytest.mark.parametrize("authority", ["executed", "filed", "draft"])
def test_context_source_cannot_be_classified(authority: str) -> None:
    pack = make_pack("none-declared")
    review = reassess(make_review("none-declared", pack), "context", authority)
    line = f"Context source cannot be classified {authority}"
    assert line in validate_review(pack, review)
    assert validate_review(pack, make_review("none-declared", pack)) == ()
