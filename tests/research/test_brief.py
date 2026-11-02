"""O7b-1a: brief tailoring merge, ordering, 1-32, lock and edit-after-lock (expected.json#brief)."""

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest

from deploy_workflow.research import brief as b
from deploy_workflow.research import contracts as c

ANCHOR = c.Anchor(cp0_sha256="a" * 64, cp1_sha256="b" * 64)


def tailored(submissions: dict[str, Any], limit: int | None = None) -> list[b.TailoredQuestion]:
    rows = submissions["brief"]["model_tailored"][:limit]
    return [b.TailoredQuestion(r["question_id"], r["text"], r["kind"]) for r in rows]


def lock(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], **over: Any
) -> c.ResearchBrief:
    args: dict[str, Any] = {
        "issuer_id": manifest["run"]["issuer_id"],
        "run_id": manifest["run"]["run_id"],
        "as_of": date(2026, 1, 10),
        "cutoff": date(2026, 1, 10),
        "context_questions": [
            (q["text"], q["focus_module"]) for q in manifest["context"]["research_questions"]
        ],
        "tailored": tailored(submissions),
        "anchor": ANCHOR,
        "path": tmp_path / "research" / "brief.json",
    }
    return b.lock_brief(**{**args, **over})


def test_forty_tailored_lock_to_thirty_two_with_context_kept(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    key = expected["brief"]["lock"]
    assert len(submissions["brief"]["model_tailored"]) + 2 == key["tailored_in"]
    ids = [q.question_id for q in lock(tmp_path, manifest, submissions).questions]
    assert ids == key["locked_ids"] and len(ids) == c.MAX_QUESTIONS
    assert not set(key["dropped_from_tail"]) & set(ids)


def test_default_brief_matches_the_key(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    key = expected["brief"]
    brief = lock(tmp_path, manifest, submissions, tailored=tailored(submissions, 6))
    assert [q.question_id for q in brief.questions] == key["question_ids"]
    assert [q.kind for q in brief.questions] == key["kinds"]
    assert {q.question_id: list(q.receivers) for q in brief.questions} == key["receivers"]
    assert {q.question_id: q.focus_module for q in brief.questions} == key["focus_modules"]
    assert (brief.version, brief.cutoff.isoformat(), brief.as_of.isoformat()) == (
        key["version"],
        key["cutoff"],
        key["as_of"],
    )
    assert brief.peer_pack is key["peer_pack"] and brief.anchor == ANCHOR
    assert brief.questions[0].text == manifest["context"]["research_questions"][0]["text"]


def test_lock_writes_a_file_that_loads_back(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any]
) -> None:
    brief = lock(tmp_path, manifest, submissions)
    path = tmp_path / "research" / "brief.json"
    assert json.loads(path.read_text(encoding="utf-8"))["brief_sha256"] == brief.brief_sha256
    assert b.load_locked_brief(path, brief.brief_sha256) == brief
    with pytest.raises(c.BriefInvalid, match="already locked"):
        lock(tmp_path, manifest, submissions)


def test_rule_vector_hash_and_edit_after_lock_equal_the_key(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    vector = expected["brief"]["rule_vector_not_a_case_value"]
    key = expected["brief"]["edit_after_lock"]
    stored = b.rebuild_brief(vector["body"])
    canonical = json.dumps(vector["body"], sort_keys=True, separators=(",", ":"))
    assert canonical == vector["canonical_text"]
    assert stored.brief_sha256 == vector["brief_sha256"] == key["edit_vector"]["stored_sha256"]
    path = tmp_path / "brief.json"
    b.write_locked_brief(path, stored)
    body = json.loads(path.read_text(encoding="utf-8"))
    body["questions"][0]["text"] = key["edit_vector"]["edited_question_text"]
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(c.BriefInvalid) as caught:
        b.load_locked_brief(path, stored.brief_sha256)
    assert str(caught.value) == key["message"]
    assert b.rebuild_brief(body).brief_sha256 == key["edit_vector"]["recomputed_sha256"]
    # Rewriting the stored hash as well is still caught against the hash recorded at the lock.
    body["brief_sha256"] = key["edit_vector"]["recomputed_sha256"]
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(c.BriefInvalid, match="^hash mismatch$"):
        b.load_locked_brief(path, stored.brief_sha256)


def test_tail_is_dropped_never_context(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any]
) -> None:
    many = [b.TailoredQuestion(f"d{i}", f"tail {i}", "custom") for i in range(40)]
    ids = [q.question_id for q in lock(tmp_path, manifest, submissions, tailored=many).questions]
    assert ids[:2] == ["ctx-1", "ctx-2"] and ids[2:] == [f"d{i}" for i in range(30)]


@pytest.mark.parametrize(
    ("over", "match"),
    [
        ({"context_questions": [], "tailored": []}, "1-32"),
        ({"context_questions": [(f"q{i}", "CP-DR") for i in range(33)]}, "context"),
        ({"context_questions": [("q", "CP-9")]}, "focus_module"),
        ({"tailored": [b.TailoredQuestion("x", "t", "context")]}, "context"),
        ({"tailored": [b.TailoredQuestion("ctx-1", "t", "custom")]}, "ctx-"),
        (
            {"tailored": [b.TailoredQuestion("x", "a", "custom")] * 2},
            "repeats",
        ),
    ],
)
def test_invalid_briefs_are_refused_and_nothing_is_written(
    tmp_path: Path,
    manifest: dict[str, Any],
    submissions: dict[str, Any],
    over: dict[str, Any],
    match: str,
) -> None:
    with pytest.raises(c.BriefInvalid, match=match):
        lock(tmp_path, manifest, submissions, **over)
    assert not (tmp_path / "research" / "brief.json").exists()


def test_every_hashed_field_edit_is_hash_mismatch(tmp_path: Path, expected: dict[str, Any]) -> None:
    vector = expected["brief"]["rule_vector_not_a_case_value"]["body"]
    stored = b.rebuild_brief(vector)
    edits: dict[str, Any] = {
        "peer_pack": lambda d: d.__setitem__("peer_pack", True),
        "peer_pack_str": lambda d: d.__setitem__("peer_pack", "yes"),
        "as_of": lambda d: d.__setitem__("as_of", "2026-01-09"),
        "version": lambda d: d.__setitem__("version", "cp-dr/2026-11-01"),
        "anchor": lambda d: d["anchor"].__setitem__("cp0_sha256", "A" * 64),
        "no_questions": lambda d: d.__setitem__("questions", []),
        "receivers": lambda d: d["questions"][0].__setitem__("receivers", []),
        "extra": lambda d: d.__setitem__("note", "added"),
        "anchor_removed": lambda d: d.pop("anchor"),
    }
    for name, edit in edits.items():
        path = tmp_path / f"{name}.json"
        b.write_locked_brief(path, stored)
        body = json.loads(path.read_text(encoding="utf-8"))
        edit(body)
        path.write_text(json.dumps(body), encoding="utf-8")
        with pytest.raises(c.BriefInvalid) as caught:
            b.load_locked_brief(path, stored.brief_sha256)
        assert str(caught.value) == expected["brief"]["edit_after_lock"]["message"], name


@pytest.mark.parametrize("content", ["[1, 2]", '{"questions": [', "\xff"])
def test_non_object_or_truncated_file_is_hash_mismatch(tmp_path: Path, content: str) -> None:
    path = tmp_path / "brief.json"
    path.write_bytes(content.encode("latin-1"))
    with pytest.raises(c.BriefInvalid, match="^hash mismatch$"):
        b.load_locked_brief(path, "0" * 64)


def test_brief_file_bytes_equal_the_keys_template(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    key = expected["cases"]["positive"]["brief"]
    assert hashlib.sha256(key["template_file"].encode()).hexdigest() == key["template_file_sha256"]
    brief = lock(tmp_path, manifest, submissions, tailored=tailored(submissions, 6))
    want = (
        key["template_file"]
        .replace("{{CP0_RESULT_SHA256}}", ANCHOR.cp0_sha256)
        .replace("{{CP1_RESULT_SHA256}}", ANCHOR.cp1_sha256)
        .replace("{{BRIEF_SHA256}}", brief.brief_sha256)
    )
    assert (tmp_path / "research" / "brief.json").read_text(encoding="utf-8") == want


def test_thirty_two_context_questions_keep_every_one(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any]
) -> None:
    ctx = [(f"context question {i}", "CP-DR") for i in range(c.MAX_QUESTIONS)]
    brief = lock(tmp_path, manifest, submissions, context_questions=ctx)
    assert [q.question_id for q in brief.questions] == [
        f"ctx-{i}" for i in range(1, c.MAX_QUESTIONS + 1)
    ]


@pytest.mark.parametrize(
    "bad",
    [
        b.TailoredQuestion("x", "t", "context"),
        b.TailoredQuestion("ctx-9", "t", "custom"),
        b.TailoredQuestion("t0", "t", "custom"),
        b.TailoredQuestion("bad id", "t", "custom"),
        b.TailoredQuestion("x1", "", "custom"),
        b.TailoredQuestion("x2", "t", cast(Any, "default_9")),
    ],
)
def test_a_malformed_question_past_the_cut_is_refused_not_dropped(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], bad: b.TailoredQuestion
) -> None:
    good = [b.TailoredQuestion(f"t{i}", f"q{i}", "custom") for i in range(40)]
    with pytest.raises(c.BriefInvalid):
        lock(tmp_path, manifest, submissions, tailored=[*good, bad])
    assert not (tmp_path / "research" / "brief.json").exists()


def test_a_changed_stored_hash_alone_is_hash_mismatch(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    stored = b.rebuild_brief(expected["brief"]["rule_vector_not_a_case_value"]["body"])
    path = tmp_path / "brief.json"
    b.write_locked_brief(path, stored)
    body = json.loads(path.read_text(encoding="utf-8"))
    body["brief_sha256"] = "0" * 64
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(c.BriefInvalid, match="^hash mismatch$"):
        b.load_locked_brief(path, stored.brief_sha256)
