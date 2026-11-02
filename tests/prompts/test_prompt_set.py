"""O6 Q3: ``PROMPT_SET_SHA256`` equals its golden, and moves with any byte of the prompt set.

The golden (``prompt_set.golden.json``) is written from the tree at the commit that added it. The
Phase 8 rules batch (P8T6-R3) edits ``rule_lists/restructuring_fulcrum.json`` and
``texts/restructuring_fulcrum.md``, so the value moves when it lands; the Release 3 golden
refresh (B28) re-pins it at the cut.
"""

import json
from pathlib import Path

import pytest

from deploy_workflow.prompts import digest

GOLDEN = Path(__file__).with_name("prompt_set.golden.json")


def test_the_prompt_set_digest_is_the_golden() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert digest.PROMPT_SET_SHA256 == golden["PROMPT_SET_SHA256"]
    assert digest.compute_prompt_set_sha256() == golden["PROMPT_SET_SHA256"]
    assert golden["files"] == len(digest.prompt_set_files())


def test_the_set_holds_the_texts_the_rule_lists_and_the_orchestrator_rules() -> None:
    names = {p.relative_to(digest._ROOT).as_posix() for p in digest.prompt_set_files()}
    assert "rule_lists/compose.json" in names  # the O rules
    assert any(n.startswith("texts/") for n in names)
    assert sum(n.startswith("rule_lists/") for n in names) >= 26


def test_one_changed_byte_moves_the_digest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "texts").mkdir()
    (tmp_path / "rule_lists").mkdir()
    (tmp_path / "texts" / "a.md").write_bytes(b"one\n")
    (tmp_path / "rule_lists" / "a.json").write_bytes(b"[]")
    monkeypatch.setattr(digest, "_ROOT", tmp_path)
    before = digest.compute_prompt_set_sha256()
    (tmp_path / "texts" / "a.md").write_bytes(b"One\n")
    assert digest.compute_prompt_set_sha256() != before
