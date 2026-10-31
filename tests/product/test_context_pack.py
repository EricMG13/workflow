"""``context_facts``: the typed context read back from a frozen pack."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal

import pytest

from deploy_vii.contracts import Source
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare
from deploy_workflow.context import (
    CONTEXT_SOURCE_ID,
    ContextRefused,
    context_facts,
    load_context,
    preparation_request,
)

CASES = Path(__file__).resolve().parents[2] / "cases" / "context"
FIX_MINIMAL = (CASES / "research-minimal.json").read_bytes()
FIX_FULL = (CASES / "primary-full.json").read_bytes()


def _pack(tmp_path: Path, raw: bytes, *, with_filing: bool = False) -> PreparedPack:
    root = tmp_path / "root"
    root.mkdir()
    (root / "context.json").write_bytes(raw)
    sources: tuple[SourceRequest, ...] = ()
    if with_filing:
        (root / "filing.txt").write_text("Revenue was 100.", encoding="utf-8")
        sources = (SourceRequest(source_id="filing", path="filing.txt", media_type="text/plain"),)
    request = preparation_request(
        load_context(raw), run_id="ctx-run-1", context_path="context.json", sources=sources
    )
    return prepare(request, root, tmp_path / "pack")


def _context_index(pack: PreparedPack) -> int:
    return next(i for i, s in enumerate(pack.sources) if s.source_id == CONTEXT_SOURCE_ID)


def _without_context(pack: PreparedPack) -> PreparedPack:
    kept = tuple(s for s in pack.sources if s.source_id != CONTEXT_SOURCE_ID)
    return pack.model_copy(update={"sources": kept})


def test_pack_without_context_gives_none(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FIX_MINIMAL, with_filing=True)
    assert context_facts(_without_context(pack)) is None


def test_frozen_context_read_back(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FIX_FULL, with_filing=True)
    assert context_facts(pack) == load_context(FIX_FULL)


def test_crlf_and_bom_file_reads_the_same(tmp_path: Path) -> None:
    text = FIX_MINIMAL.decode("utf-8")
    pretty = text.replace("{", "{\n", 1)  # a raw line break between tokens
    assert "\n" in pretty
    saved = b"\xef\xbb\xbf" + pretty.replace("\n", "\r\n").encode("utf-8")
    pack = _pack(tmp_path, saved)
    assert context_facts(pack) == load_context(FIX_MINIMAL)


@pytest.mark.parametrize(
    ("update", "field"),
    [
        ({"as_of": dt.date(2026, 1, 2)}, "run.as_of"),
        ({"issuer_id": "other-issuer"}, "identity.issuer_id"),
        ({"issuer_name": "Other Name"}, "identity.issuer_name"),
        ({"case_kind": "synthetic"}, "run.case_kind"),
        ({"pathway": "relative_value"}, "run.pathway"),
    ],
)
def test_context_not_matching_run_refused(
    tmp_path: Path, update: dict[str, object], field: str
) -> None:
    pack = _pack(tmp_path, FIX_FULL)
    run = pack.run.model_copy(update=update)
    for key, value in update.items():
        assert getattr(pack.run, key) != value  # the change must be a real mismatch
    with pytest.raises(ContextRefused) as refused:
        context_facts(pack.model_copy(update={"run": run}))
    assert [p.split(":")[0] for p in refused.value.problems] == [field]


def test_every_mismatch_is_collected(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FIX_FULL)
    run = pack.run.model_copy(update={"as_of": dt.date(2026, 1, 2), "issuer_id": "other-issuer"})
    with pytest.raises(ContextRefused) as refused:
        context_facts(pack.model_copy(update={"run": run}))
    assert {p.split(":")[0] for p in refused.value.problems} == {"run.as_of", "identity.issuer_id"}


@pytest.mark.parametrize("status", ["missing", "unreadable"])
def test_unready_context_refused(tmp_path: Path, status: Literal["missing", "unreadable"]) -> None:
    pack = _pack(tmp_path, FIX_MINIMAL)
    index = _context_index(pack)
    broken = Source(
        source_id=CONTEXT_SOURCE_ID,
        name="context.json",
        status=status,
        limitation="not available",
    )
    sources = (*pack.sources[:index], broken, *pack.sources[index + 1 :])
    with pytest.raises(ContextRefused) as refused:
        context_facts(pack.model_copy(update={"sources": sources}))
    assert CONTEXT_SOURCE_ID in str(refused.value)


def test_edited_frozen_text_is_revalidated(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FIX_MINIMAL)
    index = _context_index(pack)
    source = pack.sources[index]
    span = source.spans[0].model_copy(update={"text": "not json"})
    edited = source.model_copy(update={"spans": (span, *source.spans[1:])})
    sources = (*pack.sources[:index], edited, *pack.sources[index + 1 :])
    with pytest.raises(ContextRefused):
        context_facts(pack.model_copy(update={"sources": sources}))


def test_two_context_sources_refused(tmp_path: Path) -> None:
    pack = _pack(tmp_path, FIX_MINIMAL)
    # PreparedPack forbids duplicate ids at validation; model_copy skips validation.
    doubled = pack.model_copy(
        update={"sources": (*pack.sources, pack.sources[_context_index(pack)])}
    )
    with pytest.raises(ContextRefused):
        context_facts(doubled)
