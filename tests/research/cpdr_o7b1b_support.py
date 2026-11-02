"""Builders over the frozen cpdr-research-owner oracle for the O7b-1b tests (values read, not typed)."""

import json
from datetime import date
from typing import Any

from deploy_vii.contracts import Source, Span
from deploy_workflow.research import contracts as c
from deploy_workflow.research.brief import rebuild_brief

CP0 = "c" * 64
CP1 = "d" * 64
MARKERS = {"{{CP0_RESULT_SHA256}}": CP0, "{{CP1_RESULT_SHA256}}": CP1}


def sources(manifest: dict[str, Any]) -> tuple[Source, ...]:
    """The three accepted evidence items as prepared text/plain sources: spans line:1..line:N."""
    built = []
    for number, entry in enumerate(manifest["evidence"][:3], 1):
        lines = entry["pages"][0]["text"].split("\n")
        built.append(
            Source(
                source_id=f"ev-{number}",
                name=entry["path"],
                status="ready",
                sha256=entry["page_join_sha256"],
                media_type="text/plain",
                spans=tuple(Span(locator=f"line:{n}", text=t) for n, t in enumerate(lines, 1)),
            )
        )
    return tuple(built)


def evidence(expected: dict[str, Any]) -> tuple[c.EvidenceItem, ...]:
    return tuple(
        c.EvidenceItem(
            item_id=a["item_id"],
            origin="supplied",
            sha256=a["sha256"],
            locator=a["locator"],
            published=date.fromisoformat(a["published"]),
            family=a["family"],
        )
        for a in expected["intake"]["accepted"]
    )


def brief(expected: dict[str, Any], case: str = "positive") -> c.ResearchBrief:
    template = json.loads(expected["cases"][case]["brief"]["template_file"])
    fixed = json.loads(json.dumps(template))
    for key, value in MARKERS.items():
        marker = key
        for field in ("cp0_sha256", "cp1_sha256"):
            if fixed["anchor"][field] == marker:
                fixed["anchor"][field] = value
    return rebuild_brief(fixed)
