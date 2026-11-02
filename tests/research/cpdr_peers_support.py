"""Builders over the frozen cpdr-peers-owner oracle for the O7d tests (values read, not typed)."""

import copy
import json
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

from cpdr_o7b1b_support import sources

from deploy_workflow.research import contracts as c
from deploy_workflow.research import peers as p
from deploy_workflow.research import review
from deploy_workflow.research import tables as t
from deploy_workflow.research.brief import TailoredQuestion, merge_questions

CASE = Path(__file__).resolve().parents[2] / "cases" / "cpdr-peers-owner"
CP0, CP1 = "c" * 64, "d" * 64
MARKERS = {"{{CP0_RESULT_SHA256}}": CP0, "{{CP1_RESULT_SHA256}}": CP1}
KEY_FIELDS = (
    "fact_id",
    "table_id",
    "row_id",
    "field",
    "label",
    "text",
    "status",
    "unit",
    "currency",
    "period",
    "value_class",
    "limitation",
)


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((CASE / name).read_text(encoding="utf-8"))
    return data


def make_brief(key: dict[str, Any], subs: dict[str, Any], *, peer_pack: bool) -> c.ResearchBrief:
    rows = subs["brief"]["model_tailored_defaults_only"]
    context = [(q["text"], q["focus_module"]) for q in subs["brief"]["context_research_questions"]]
    questions = merge_questions(
        context, [TailoredQuestion(r["question_id"], r["text"], r["kind"]) for r in rows]
    )
    anchor = {n: MARKERS[v] for n, v in key["brief"]["anchor"].items()}
    run = load("manifest.json")["run"]
    return c.ResearchBrief.build(
        issuer_id=run["issuer_id"],
        run_id=run["run_id"],
        as_of=date.fromisoformat(key["brief"]["as_of"]),
        cutoff=date.fromisoformat(key["brief"]["cutoff"]),
        questions=questions,
        anchor=anchor,
        peer_pack=peer_pack,
    )


def accepted(key: dict[str, Any]) -> tuple[c.EvidenceItem, ...]:
    return tuple(
        c.EvidenceItem(
            item_id=a["id"],
            origin="supplied",
            sha256=a["sha256"],
            locator=a["locator"],
            published=date.fromisoformat(a["published"]),
            family=a["family"],
        )
        for a in key["intake"]["accepted"]
    )


class Case:
    """The key submission, the locked brief, the accepted evidence and the held sources."""

    def __init__(self, key: dict[str, Any], subs: dict[str, Any], manifest: dict[str, Any]) -> None:
        self.key = key
        self.body = copy.deepcopy(subs["research_peers"])
        self.refusals = subs["refusal_inputs"]
        self.brief = make_brief(key, subs, peer_pack=True)
        self.plain = make_brief(key, subs, peer_pack=False)
        self.evidence = accepted(key)
        self.sources = sources(manifest)

    def submission(self, body: dict[str, Any] | None = None) -> review.ResearchSubmission:
        return review.ResearchSubmission.parse(body or self.body)

    def pack(self, body: dict[str, Any] | None = None) -> p.PeerPack:
        pack = self.submission(body).peers
        assert pack is not None
        return pack

    def issues(
        self, body: dict[str, Any] | None = None, brief: c.ResearchBrief | None = None
    ) -> Any:
        return p.peer_issues(
            self.submission(body).peers, brief or self.brief, self.evidence, self.sources
        )

    def composed(self, body: dict[str, Any] | None = None) -> t.Composed:
        return p.compose_peer_tables(
            self.pack(body), {i.item_id: i for i in self.evidence}, self.brief.cutoff
        )

    def replaced(self, section: str, refusal: str, index: int = 0) -> dict[str, Any]:
        """The key submission with the refusal input in place of the same-position entry."""
        body: dict[str, Any] = copy.deepcopy(self.body)
        body["peers"][section][index] = copy.deepcopy(self.refusals[refusal])
        return body


@cache
def peers_case() -> Case:
    """The oracle read once; callers copy a body before editing it."""
    return Case(load("expected.json"), load("submissions.json"), load("manifest.json"))
