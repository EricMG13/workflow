"""CZR driver: the pack builds deterministically, hashes and pages hold, the CP-1 precheck
locates the statement pages and the extractor reads them; every CP-1 citation key lies in
exactly one page. No run is driven here (`czr_closed` needs Workflow Test's submissions)."""

import hashlib
import json
import re
from pathlib import Path

import czr_runs
import pytest

from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow.financial_workflow import STATEMENT_HEADING

CASE = czr_runs.CASE
QUALIFICATION = json.loads((CASE / "qualification.json").read_text(encoding="utf-8"))
EXPECTS = QUALIFICATION["cases"][0]["expects"]
SOURCE_OF = {d["sha256"]: d["source_id"] for d in czr_runs.manifest()["documents"]}
TEN_Q, TEN_K = "czr-q2-2026-10q", "czr-fy2025-10k"

PACK = czr_runs.make_pack()
SPANS = {s.source_id: {span.locator: span.text for span in s.spans} for s in PACK.sources}

assert EXPECTS, "qualification expects is empty"


def test_pack_builds_deterministically() -> None:
    again = czr_runs.make_pack()
    assert again.content_hash() == PACK.content_hash()
    assert again == PACK
    run = PACK.run
    assert (run.case_kind, run.pathway, run.requested_modules) == (
        "public",
        "earnings_update",
        ("CP-1",),
    )
    assert str(run.as_of) == czr_runs.manifest()["run"]["as_of"]
    assert run.run_id == czr_runs.RUN_ID != czr_runs.manifest()["run"]["run_id"]


def test_source_hashes_equal_the_qualification_hashes() -> None:
    assert len(QUALIFICATION["cases"][0]["documents"]) == 3
    assert {s.sha256 for s in PACK.sources} == set(SOURCE_OF)
    for source in PACK.sources:
        item = next(
            d for d in czr_runs.manifest()["documents"] if d["source_id"] == source.source_id
        )
        assert source.sha256 == hashlib.sha256((CASE / item["path"]).read_bytes()).hexdigest()
    assert {e["document_sha256"] for e in EXPECTS} <= set(SOURCE_OF)


def test_pages_rule_on_a_small_text() -> None:
    raw = (
        b"intro\n7\nCAESARS\nCONSOLIDATED CONDENSED BALANCE SHEETS\nrow\n"
        b"CONSOLIDATED STATEMENTS OF CASH FLOWS\n12\n"
    )
    assert czr_runs.pages(raw) == [
        "intro\n7",
        "CAESARS",
        "CONSOLIDATED CONDENSED BALANCE SHEETS\nrow",
        "CONSOLIDATED STATEMENTS OF CASH FLOWS\n12",
    ]
    assert czr_runs.pages(b"2026\n") == ["2026"]
    assert czr_runs.pages(b"CONSOLIDATED BALANCE SHEETS\nx") == ["CONSOLIDATED BALANCE SHEETS\nx"]


def test_pages_cover_the_bytes_exactly() -> None:
    for item in czr_runs.manifest()["documents"]:
        raw = (CASE / item["path"]).read_bytes()
        assert "\n".join(czr_runs.pages(raw)) + "\n" == raw.decode("utf-8")
        locators = [
            s.locator
            for s in next(x for x in PACK.sources if x.source_id == item["source_id"]).spans
        ]
        assert locators == [f"page:{n}" for n in range(1, len(locators) + 1)]


def _located(source_id: str) -> list[str]:
    return [loc for loc, text in SPANS[source_id].items() if STATEMENT_HEADING.search(text)]


@pytest.mark.parametrize("source_id", [TEN_Q, TEN_K])
def test_precheck_locates_three_statement_pages(source_id: str) -> None:
    located = _located(source_id)
    assert len(located) == 3
    headings = [
        line
        for loc in located
        for line in SPANS[source_id][loc].split("\n")
        if STATEMENT_HEADING.fullmatch(line)
    ]
    assert [re.sub(r"^CONSOLIDATED (CONDENSED )?", "", h) for h in headings] == [
        "BALANCE SHEETS",
        "STATEMENTS OF OPERATIONS",
        "STATEMENTS OF CASH FLOWS",
    ]
    for loc in located:
        first = SPANS[source_id][loc].split("\n")[0]
        assert STATEMENT_HEADING.fullmatch(first), (
            f"{source_id} {loc} does not start at its heading"
        )


@pytest.mark.parametrize("source_id", [TEN_Q, TEN_K])
def test_extraction_returns_lines_for_each_located_page(source_id: str) -> None:
    for loc in _located(source_id):
        table = extract_statement_lines(SPANS[source_id][loc], loc, source_id=source_id)
        assert len(table.lines) >= 10, (source_id, loc, len(table.lines))
        assert table.headers, (source_id, loc)


def _pages_holding(source_id: str, text: str) -> list[str]:
    return [loc for loc, page in SPANS[source_id].items() if text in page]


def _candidates(expect: dict[str, object]) -> list[tuple[str, str]]:
    found = [(str(expect["document_sha256"]), str(expect["matched_text"]))]
    alternatives = expect.get("alternatives", [])
    assert isinstance(alternatives, list)
    found += [(a["document_sha256"], a["matched_text"]) for a in alternatives]
    return found


@pytest.mark.parametrize("n", range(len(EXPECTS)))
def test_each_cp1_key_lies_in_exactly_one_page(n: int) -> None:
    expect = EXPECTS[n]
    if expect["module_id"] != "CP-1":
        pytest.skip("not a CP-1 key")
    counts = [len(_pages_holding(SOURCE_OF[sha], text)) for sha, text in _candidates(expect)]
    assert 1 in counts, (expect["matched_text"], counts)


def test_czr_closed_without_submissions_raises_naming_the_file(tmp_path: Path) -> None:
    if czr_runs.SUBMISSIONS.exists():
        pytest.skip("submissions.json exists; the run is exercised by Workflow Test")
    with pytest.raises(FileNotFoundError, match="submissions.json"):
        czr_runs.czr_closed(tmp_path)
    assert not any(tmp_path.iterdir())
