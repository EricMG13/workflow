"""O7b-1b Behaviour 9: dossier, brief.json and readiness (expected.json#cases/*/dossier, #ceiling)."""

import copy
import hashlib
import json
from datetime import date
from typing import Any

import pytest
from cpdr_o7b1b_support import brief, evidence

from deploy_workflow.prompts.fence import FenceError
from deploy_workflow.research import contracts as c
from deploy_workflow.research import dossier as d
from deploy_workflow.research.intake import RefusedItem

BRIEF_MARKER = "{{BRIEF_SHA256}}"


def rejected(expected: dict[str, Any]) -> tuple[RefusedItem, ...]:
    return tuple(
        RefusedItem(
            locator=e["locator"],
            family=e["family"],
            published=date.fromisoformat(e["published"]) if e["published"] else None,
            reason=e["reason"],
        )
        for e in expected["intake"]["rejected_json"]["entries"]
    )


def build(expected: dict[str, Any], case: str, **over: Any) -> tuple[d.DossierInput, str]:
    key = expected["cases"][case]
    locked = brief(expected, case)
    text = key["dossier"]["template_text"].replace(BRIEF_MARKER, locked.brief_sha256)
    args: dict[str, Any] = {
        "brief": locked,
        "claim_states": tuple(key["claim_state_list"]),
        "tables": key["tables"],
        "facts": key["facts"],
        "evidence": evidence(expected),
        "rejected": rejected(expected),
        "head_sha256": "e" * 64,  # the head's Module.content_hash(): recorded, not compared
        "head_brief_sha256": locked.brief_sha256,
    }
    return d.DossierInput(**{**args, **over}), text


@pytest.mark.parametrize("case", ["positive", "v2"])
def test_dossier_bytes_are_the_key_and_its_hash_is_its_own(
    case: str, expected: dict[str, Any]
) -> None:
    key = expected["cases"][case]["dossier"]
    assert hashlib.sha256(key["template_text"].encode()).hexdigest() == key["template_sha256"]
    given, text = build(expected, case)
    out = d.render_dossier(given)
    assert out.markdown == text
    assert out.markdown.encode("utf-8").endswith(b"\n") and "\r" not in out.markdown
    assert out.dossier_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert out.dossier_sha256 != given.head_sha256  # O7-R10: the head keeps deploy_vii's hash
    assert out.readiness == expected["cases"][case]["readiness"]
    assert out.lineage == "LOCAL" == expected["cp_dr_lineage"]


@pytest.mark.parametrize("case", ["positive", "v2"])
def test_brief_json_is_the_key_file(case: str, expected: dict[str, Any]) -> None:
    template = expected["cases"][case]["brief"]["template_file"]
    given, _ = build(expected, case)
    want = (
        template.replace("{{CP0_RESULT_SHA256}}", "c" * 64)
        .replace("{{CP1_RESULT_SHA256}}", "d" * 64)
        .replace(BRIEF_MARKER, given.brief.brief_sha256)
    )
    out = d.render_dossier(given)
    assert out.brief_json == want
    assert json.loads(out.brief_json)["brief_sha256"] == given.brief.brief_sha256
    assert out.brief_file_sha256 == hashlib.sha256(want.encode("utf-8")).hexdigest()


def test_a_head_bound_to_another_brief_is_refused(expected: dict[str, Any]) -> None:
    """O7-R10: the content binding is the dossier's brief_sha256 equal to the head's
    research-brief input; the head's own hash is recorded and never compared."""
    given, _ = build(expected, "positive", head_brief_sha256="0" * 64)
    with pytest.raises(d.DossierMismatch, match="research-brief"):
        d.render_dossier(given)


def test_any_head_hash_is_recorded_not_compared(expected: dict[str, Any]) -> None:
    for head in ("0" * 64, "f" * 64):
        given, text = build(expected, "positive", head_sha256=head)
        assert d.render_dossier(given).markdown == text


def test_readiness_is_never_committee_ready_and_blocked_when_a_question_blocks(
    expected: dict[str, Any],
) -> None:
    given, _ = build(expected, "positive", claim_states=("supported",) * 8)
    assert "readiness: RESEARCH_READY\n" in d.dossier_markdown(given)
    assert "COMMITTEE_READY" not in d.dossier_markdown(given)
    blocked, _ = build(expected, "positive", claim_states=())
    assert "readiness: BLOCKED\n" in d.dossier_markdown(blocked)
    with pytest.raises(c.CommitteeReadyRefused):
        c.Dossier(brief_sha256="a" * 64, lineage="LOCAL", readiness="COMMITTEE_READY")


def test_a_cell_that_would_break_the_table_is_refused(expected: dict[str, Any]) -> None:
    given, _ = build(expected, "positive")
    tables = copy.deepcopy(given.tables)
    tables["TDR.1"]["rows"][0][1]["text"]["shown"] = "a | b"
    bad, _ = build(expected, "positive", tables=tables)
    with pytest.raises(d.DossierInvalid, match="TDR.1"):
        d.dossier_markdown(bad)


def test_a_missing_table_is_refused(expected: dict[str, Any]) -> None:
    given, _ = build(expected, "positive")
    tables = {k: v for k, v in given.tables.items() if k != "TDR.2"}
    bad, _ = build(expected, "positive", tables=tables)
    with pytest.raises(d.DossierInvalid, match="TDR.2"):
        d.dossier_markdown(bad)


def terminator_item(expected: dict[str, Any], manifest: dict[str, Any]) -> RefusedItem:
    suffix = expected["refusals"]["research"]["fence_terminator"]["reason_suffix"]
    item = manifest["fence_terminator_item"]
    return RefusedItem(
        locator=item["locator"],
        family=item["family"],
        published=date.fromisoformat(item["published"]),
        reason=f"evidence item {item['locator']} {suffix}",
    )


def test_a_reason_holding_the_terminator_shows_the_keys_label(
    expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    """O7-R6: the dossier shows ``#refusals/research/fence_terminator/dossier_shown_reason`` in
    place of the reason; the refused item's row keeps its locator, family and date."""
    refused = terminator_item(expected, manifest)
    label = expected["refusals"]["research"]["fence_terminator"]["dossier_shown_reason"]
    given, _ = build(expected, "positive")
    shown, _ = build(expected, "positive", rejected=(*given.rejected, refused))
    text = d.dossier_markdown(shown)
    assert f"| {refused.locator} | {refused.family} | {refused.published} | {label} |" in text
    assert "<<<" not in text and refused.reason not in text
    assert d.render_dossier(shown).markdown == text


def test_another_block_opener_in_a_reason_is_still_refused(expected: dict[str, Any]) -> None:
    given, _ = build(expected, "positive")
    odd = RefusedItem("https://x.example/a", "f", None, "reason with <<<SOURCE inside")
    bad, _ = build(expected, "positive", rejected=(*given.rejected, odd))
    with pytest.raises(d.DossierInvalid, match="block delimiter"):
        d.dossier_markdown(bad)


def test_a_dossier_the_fence_refuses_is_dossier_invalid(
    expected: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """O7-R23(b): render_dossier runs the dossier through ``data_block``; a FenceError is
    ``DossierInvalid``."""
    seen: list[tuple[str, str]] = []

    def refuse(kind: str, block_id: str, body: str) -> str:
        seen.append((kind, block_id))
        raise FenceError("refused by the fence")

    monkeypatch.setattr(d, "data_block", refuse)
    given, _ = build(expected, "positive")
    with pytest.raises(d.DossierInvalid, match="refused by the fence"):
        d.render_dossier(given)
    assert seen == [("CONTEXT", "cp-dr-dossier")]
