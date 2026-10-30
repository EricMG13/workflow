"""CZR driver: the pack builds deterministically, hashes and pages hold, the CP-1 precheck
locates the statement pages and the extractor reads them; every CP-1 citation key lies in
exactly one page; the item 70 run plans CP-0, CP-1, CP-1A, CP-2, CP-5; the figure binder and
the stage loop are tested over a `submissions.json` written under tmp_path. No full run is
driven here (`czr_closed` needs Workflow Test's submissions in `cases/`)."""

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path

import czr_runs
import pytest

from deploy_vii.contracts import Fact
from deploy_vii.registry import plan
from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow.financial_workflow import STATEMENT_HEADING
from deploy_workflow.owner_workflow import OwnerWorkflow, WorkflowError

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
        ("CP-1", "CP-2", "CP-5"),
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


def test_item_70_run_id_and_plan() -> None:
    assert czr_runs.RUN_ID == "czr-2026q2-earnings-update-v1"
    assert PACK.run.run_id == czr_runs.RUN_ID
    assert plan(PACK.run.requested_modules) == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-5")


# --- figure binder ---------------------------------------------------------------------------

SELECTOR = {
    "module_id": "CP-1",
    "table_id": "T1",
    "period": "Q2 26",
    "label": "Revenue",
    "unit_token": "USD_M",
    "spelled": "$2,900",
}
BODY: dict[str, object] = {"cp1_facts": [{"ref": "f1", "unit": "USD_M", "shown": "$2,900"}]}


def _fact(fact_id: str, label: str = "Revenue", period: str = "Q2 26") -> Fact:
    return Fact(fact_id=fact_id, label=label, table_id="T1", period=period)


def _facts_of(*facts: Fact) -> Callable[[str], tuple[Fact, ...]]:
    def facts_of(module_id: str) -> tuple[Fact, ...]:
        assert module_id == "CP-1"
        return facts

    return facts_of


def test_binder_binds_exactly_one_match() -> None:
    facts_of = _facts_of(_fact("f1"), _fact("f2", label="Other"), _fact("f3", period="Q1 26"))
    out = czr_runs.bind_stage_figures(
        "rev {{FIG:rev}} and {{FIG:rev}}", {"rev": SELECTOR}, BODY, facts_of
    )
    assert out == "rev {f1|USD_M} and {f1|USD_M}"


@pytest.mark.parametrize(
    ("facts", "body", "selector", "text", "figure"),
    [
        ((_fact("f9", label="Other"),), BODY, SELECTOR, "{{FIG:rev}}", "rev"),
        ((_fact("f1"), _fact("f2")), BODY, SELECTOR, "{{FIG:rev}}", "rev"),
        ((_fact("f1"),), BODY, {**SELECTOR, "unit_token": "USD_B"}, "{{FIG:rev}}", "rev"),
        ((_fact("f1"),), BODY, {**SELECTOR, "spelled": "$1"}, "{{FIG:rev}}", "rev"),
        ((_fact("f1"),), {"cp1_facts": []}, SELECTOR, "{{FIG:rev}}", "rev"),
        ((_fact("f1"),), BODY, SELECTOR, "{{FIG:nope}}", "nope"),
        ((_fact("f1"),), None, SELECTOR, "{{FIG:rev}}", "rev"),
    ],
)
def test_binder_refuses_without_fallback(
    facts: tuple[Fact, ...],
    body: dict[str, object] | None,
    selector: dict[str, str],
    text: str,
    figure: str,
) -> None:
    with pytest.raises(RuntimeError, match=f"FIG {figure}"):
        czr_runs.bind_stage_figures(text, {"rev": selector}, body, _facts_of(*facts))


def test_binder_leaves_text_without_tokens_alone() -> None:
    assert czr_runs.bind_stage_figures("plain", {}, None, _facts_of()) == "plain"


# --- stage loop ------------------------------------------------------------------------------


def _write(path: Path, stages: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"stages": stages}), encoding="utf-8")
    return path


def test_czr_closed_wrong_step_raises(tmp_path: Path) -> None:
    sub = _write(tmp_path / "s.json", [{"step": "financials", "calls": [], "submission": {}}])
    with pytest.raises(RuntimeError, match="'financials'.*'source_readiness'"):
        czr_runs.czr_closed(tmp_path / "run", sub)


def test_czr_closed_read_inputs_call_reaches_the_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []
    real = OwnerWorkflow.read_inputs

    def spy(self: OwnerWorkflow) -> dict[str, object]:
        seen.append("read_inputs")
        return real(self)

    monkeypatch.setattr(OwnerWorkflow, "read_inputs", spy)
    sub = _write(
        tmp_path / "s.json",
        [{"step": "source_readiness", "calls": [{"tool": "read_inputs"}], "submission": {}}],
    )
    # source_readiness declares no inputs, so the workflow itself refuses the call
    with pytest.raises(WorkflowError):
        czr_runs.czr_closed(tmp_path / "run", sub)
    assert seen == ["read_inputs"]


def test_czr_closed_missing_file_names_it(tmp_path: Path) -> None:
    missing = tmp_path / "absent-submissions.json"
    with pytest.raises(FileNotFoundError, match="absent-submissions.json"):
        czr_runs.czr_closed(tmp_path / "run", missing)


def test_binder_refuses_one_ref_shown_two_ways() -> None:
    body: dict[str, object] = {
        "cp1_facts": [{"ref": "f1", "unit": "USD_M", "shown": "$2,900"}],
        "other_facts": [{"ref": "f1", "unit": "USD_M", "shown": "$2.9B"}],
    }
    with pytest.raises(RuntimeError, match="f1"):
        czr_runs.bind_stage_figures("{{FIG:rev}}", {"rev": SELECTOR}, body, _facts_of(_fact("f1")))


def test_binder_takes_refs_from_every_list() -> None:
    body: dict[str, object] = {
        "cp1_facts": [],
        "more": [{"ref": "f1", "unit": "USD_M", "shown": "$2,900"}],
    }
    facts_of = _facts_of(_fact("f1"))
    out = czr_runs.bind_stage_figures("{{FIG:rev}}", {"rev": SELECTOR}, body, facts_of)
    assert out == "{f1|USD_M}"


def test_a_step_with_inputs_must_have_read_them_before_submitting() -> None:
    with pytest.raises(RuntimeError, match="read_inputs.*financials"):
        czr_runs.require_read("financials", "projection", read_made=False)
    czr_runs.require_read("financials", "projection", read_made=True)
    czr_runs.require_read("source_readiness", "none", read_made=False)
