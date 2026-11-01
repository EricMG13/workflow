"""O7a: CP-DR additive contracts, version constant, readiness ladder, decision amendment."""

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_workflow.research import contracts as c

H0 = "a" * 64
H1 = "b" * 64
ROOT = Path(__file__).resolve().parents[2]


def question(i: int = 1, **over: Any) -> c.ResearchQuestion:
    base: dict[str, Any] = {
        "question_id": f"q{i}",
        "text": f"question {i}",
        "kind": "custom",
        "receivers": ("CP-1C",),
    }
    return c.ResearchQuestion(**{**base, **over})


def brief(n: int = 1, **over: Any) -> c.ResearchBrief:
    base: dict[str, Any] = {
        "issuer_id": "iss",
        "run_id": "run1",
        "as_of": date(2026, 11, 1),
        "cutoff": date(2026, 10, 31),
        "questions": tuple(question(i) for i in range(n)),
        "anchor": c.Anchor(cp0_sha256=H0, cp1_sha256=H1),
        "peer_pack": False,
    }
    return c.ResearchBrief.build(**{**base, **over})


def test_version_constant() -> None:
    assert c.METHOD_VERSION_CPDR == "cp-dr/2026-10-31"
    assert c.LOCAL_CEILING == "RESEARCH_READY"


def test_committee_ready_never_assigned_to_local() -> None:
    cases: list[list[c.ClaimState]] = [[], ["supported"], ["missing"], ["contrary"], ["blocked"]]
    for states in cases:
        assert c.assign_readiness(states) != "COMMITTEE_READY"
    with pytest.raises(c.CommitteeReadyRefused):
        c.Dossier(brief_sha256=H0, lineage="LOCAL", readiness="COMMITTEE_READY")
    ok = c.Dossier(brief_sha256=H0, lineage="LOCAL", readiness="RESEARCH_READY")
    assert ok.readiness == "RESEARCH_READY"


@given(st.lists(st.sampled_from(["supported", "contrary", "missing", "blocked"])))
def test_readiness_never_above_ceiling(states: list[c.ClaimState]) -> None:
    got = c.assign_readiness(states)
    assert got != "COMMITTEE_READY"
    if not states or "blocked" in states:
        assert got == "BLOCKED"
    elif "contrary" in states or "missing" in states:
        assert got == "RESEARCH_READY_WITH_LIMITATIONS"
    else:
        assert got == c.LOCAL_CEILING


def test_lineage_rejects_full_cp_os() -> None:
    with pytest.raises(ValidationError):
        c.Dossier(brief_sha256=H0, lineage="FULL_CP_OS", readiness="BLOCKED")  # type: ignore[arg-type]


def test_brief_bounds() -> None:
    with pytest.raises(c.BriefInvalid):
        brief(0)
    with pytest.raises(c.BriefInvalid):
        brief(33)
    assert len(brief(1).questions) == 1
    assert len(brief(32).questions) == 32
    with pytest.raises(c.BriefInvalid):
        brief(cutoff=date(2026, 11, 2))
    assert brief(cutoff=date(2026, 11, 1)).cutoff == date(2026, 11, 1)


def test_brief_hash_canonical() -> None:
    b = brief(2)
    body = b.model_dump(mode="json", exclude={"brief_sha256"})
    shuffled = dict(reversed(list(body.items())))
    text = json.dumps(shuffled, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert b.brief_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    changed = brief(2, questions=(question(0), question(1, text="other")))
    assert changed.brief_sha256 != b.brief_sha256
    with pytest.raises(c.BriefInvalid):
        c.ResearchBrief(**{**{k: getattr(b, k) for k in type(b).model_fields}, "brief_sha256": H0})


@pytest.mark.parametrize(
    ("focus", "expected"),
    [
        ("CP-1C", ("CP-1C",)),
        ("CP-2", ("CP-2",)),
        ("CP-DR", ("CP-1C", "CP-2")),
        ("", ("CP-1C", "CP-2")),
        ("  ", ("CP-1C", "CP-2")),
    ],
)
def test_focus_module_maps_receivers(focus: str, expected: tuple[str, ...]) -> None:
    assert c.receivers_for_focus(focus) == expected
    q = c.ResearchQuestion.from_context("q1", "t", focus)
    assert q.kind == "context" and q.receivers == expected


def test_focus_module_refuses_other() -> None:
    with pytest.raises(c.BriefInvalid):
        c.receivers_for_focus("CP-4")
    with pytest.raises(c.BriefInvalid):
        c.ResearchQuestion.from_context("q1", "t", "CP-4")


def test_context_question_receivers_checked() -> None:
    with pytest.raises(c.BriefInvalid):
        question(kind="context", receivers=("CP-1C",), focus_module="CP-2")


@pytest.mark.parametrize("sid", ["ev-1", "ev-anything", "cp-dr-dossier", "peers"])
def test_reserved_ids_refused(sid: str) -> None:
    with pytest.raises(c.ReservedSourceId):
        c.refuse_reserved(sid)


def test_unreserved_id_passes() -> None:
    c.refuse_reserved("annual-report")


def test_evidence_item_id_format() -> None:
    def item(item_id: str) -> c.EvidenceItem:
        return c.EvidenceItem(
            item_id=item_id,
            origin="supplied",
            sha256=H0,
            locator="file.pdf",
            published=None,
            family="issuer",
        )

    assert item("ev-1").published is None
    assert item("ev-12").item_id == "ev-12"
    for bad in ("ev-0", "ev-01", "ev-", "ev-x", "x-1"):
        with pytest.raises(ValidationError):
            item(bad)


def test_error_hierarchy_avoids_value_error() -> None:
    for err in (
        c.CpDrNotAnchored,
        c.BriefInvalid,
        c.CutoffViolation,
        c.CommitteeReadyRefused,
        c.EvidenceFetchRefused,
        c.ReservedSourceId,
    ):
        assert issubclass(err, c.ResearchError)
        assert not issubclass(err, ValueError)


def test_decision_amendment_states_two_anchors() -> None:
    text = (ROOT / "docs/decisions/0007-amendment-cp-dr-local-anchors.md").read_text()
    assert text.startswith("amends: 0007 standalone mode\nanchors: CP-0, CP-1\n\n")
    assert "amends: 0007 standalone mode" in text
    assert "anchors: CP-0, CP-1" in text
