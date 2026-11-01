"""Every golden quote and printed value inside one converted line (O2 done-when, part 2).

Rule: html_text.convert_html (no-div). A quote that fits no single line must be listed in
cases/goldens/line-exceptions.json; the list may only shrink. `printed` must fit one line for
every evidence, excepted or not; one that does not is listed as printed_unplaced.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.html_text import convert_html

REPO = Path(__file__).resolve().parents[1]
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")
EXCEPTIONS = REPO / "cases/goldens/line-exceptions.json"
HEAD = 90
MAX_QUOTE_EXCEPTIONS = 83  # shrink-only: lower these when the list shrinks, never raise them
MAX_PRINTED_UNPLACED = 2
Key = tuple[str, str, str, str]


def _check_py() -> Any:
    spec = importlib.util.spec_from_file_location("golden_check", REPO / "cases/goldens/check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry(case_id: str, fact_id: str, source_id: str, quote: str) -> dict[str, str]:
    return {
        "case_id": case_id,
        "fact_id": fact_id,
        "source_id": source_id,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "quote_head": quote[:HEAD],
    }


def _key(entry: dict[str, str]) -> Key:
    return (entry["case_id"], entry["fact_id"], entry["source_id"], entry["quote_sha256"])


def _line_misses(check: Any, ev: dict[str, str], lines: list[str]) -> tuple[bool, bool]:
    """(quote misses, printed misses): True where the normalised text fits no single line."""
    quote = check.normalise(ev["quote"])
    printed = check.normalise(ev["printed"])
    return (
        not any(quote in line for line in lines),
        not any(printed in line for line in lines),
    )


def _scan() -> tuple[list[dict[str, str]], list[dict[str, str]], int, int]:
    """Return (quote misses, printed misses, html evidences checked, pdf evidences not checked)."""
    check = _check_py()
    quote_misses: list[dict[str, str]] = []
    printed_misses: list[dict[str, str]] = []
    checked = pdf = 0
    for golden in sorted((REPO / "cases/goldens").glob("*/module_golden.json")):
        data = json.loads(golden.read_text(encoding="utf-8"))
        lines: dict[str, list[str]] = {}
        pdf_ids: set[str] = set()
        for source in data["sources"]:
            path = CORPUS / source["file"]
            if path.suffix.lower() == ".pdf":
                pdf_ids.add(source["source_id"])
            else:
                text = convert_html(path.read_bytes()).text
                lines[source["source_id"]] = text.splitlines()
        for fact in data["facts"]:
            for ev in fact["evidence"]:
                if ev["source_id"] in pdf_ids:
                    pdf += 1
                    continue
                checked += 1
                quote = check.normalise(ev["quote"])
                entry = _entry(data["case_id"], fact["fact_id"], ev["source_id"], quote)
                quote_missed, printed_missed = _line_misses(check, ev, lines[ev["source_id"]])
                if quote_missed:
                    quote_misses.append(entry)
                if printed_missed:
                    printed_misses.append(entry)
    return quote_misses, printed_misses, checked, pdf


def _sorted(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(entries, key=_key)


def _write_exceptions() -> None:
    """Generate the committed list from the ruled rule (run once; the list may only shrink)."""
    quote_misses, printed_misses, _, _ = _scan()
    payload = {
        "printed_unplaced": _sorted(printed_misses),
        "quote_misses": _sorted(quote_misses),
    }
    EXCEPTIONS.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _compare(found: list[dict[str, str]], listed: list[dict[str, str]], what: str) -> list[str]:
    """Problems between measured misses and the committed list (both sides as multisets)."""
    found_keys = Counter(_key(e) for e in found)
    listed_keys = Counter(_key(e) for e in listed)
    problems = []
    for key in sorted((found_keys - listed_keys).elements()):
        problems.append(f"{what} not on the exception list: {key}")
    for key in sorted((listed_keys - found_keys).elements()):
        problems.append(f"{what} exception now fits one line (remove it): {key}")
    if len(found) > len(listed):
        problems.append(f"{what}: {len(found)} misses exceed {len(listed)} exceptions")
    return problems


def _load_exceptions() -> dict[str, list[dict[str, str]]]:
    return json.loads(EXCEPTIONS.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _e(fact: str = "f1", quote: str = "alpha") -> dict[str, str]:
    return _entry("c", fact, "s", quote)


def test_compare_passes_when_lists_match() -> None:
    assert _compare([_e()], [_e()], "quote") == []


def test_compare_names_a_deleted_exception() -> None:
    problems = _compare([_e("f1"), _e("f2", "beta")], [_e("f1")], "quote")
    assert any("not on the exception list" in p and "f2" in p for p in problems)
    assert any("exceed" in p for p in problems)


def test_compare_flags_a_made_up_exception_as_fits() -> None:
    problems = _compare([_e("f1")], [_e("f1"), _e("f9", "made up")], "quote")
    assert any("now fits" in p and "f9" in p for p in problems)


def test_printed_split_across_two_lines_is_a_miss() -> None:
    lines = convert_html(b"<p>Net debt 1,2</p><p>34 million</p>").text.splitlines()
    assert not any("1,234" in line for line in lines)
    assert any("1,2" in line for line in lines)


def test_printed_check_flags_a_value_split_across_lines_without_the_corpus() -> None:
    check = _check_py()
    split = convert_html(b"<p>Net debt 1,2</p><p>34 million</p>").text.splitlines()
    whole = convert_html(b"<p>Net debt 1,234 million</p>").text.splitlines()
    ev = {"quote": "Net debt", "printed": "1,234"}
    assert _line_misses(check, ev, split) == (False, True)  # the quote fits a line; printed splits
    assert _line_misses(check, ev, whole) == (False, False)


def test_goldens_inside_one_line_with_fixed_exception_list() -> None:
    if not CORPUS.is_dir():
        pytest.skip("public corpus directory absent (artifacts/public-corpus/v1)")
    listed = _load_exceptions()
    quote_misses, printed_misses, checked, pdf = _scan()
    assert checked > 0
    # PDF quotes cannot be checked (check.py prints "not checked: pdf"); their count is reported.
    print(
        f"golden lines: html evidences {checked}, quote misses {len(quote_misses)}, "
        f"printed misses {len(printed_misses)}, pdf not checked {pdf}"
    )
    problems = _compare(quote_misses, listed["quote_misses"], "quote")
    problems += _compare(printed_misses, listed["printed_unplaced"], "printed")
    ceiling = len(listed["quote_misses"]) + len(listed["printed_unplaced"])
    if len(quote_misses) + len(printed_misses) > ceiling:
        problems.append(f"misses exceed the ceiling of {ceiling}")
    # Shrink-only: the committed list may fall below these, never rise above them.
    if len(listed["quote_misses"]) > MAX_QUOTE_EXCEPTIONS:
        problems.append(
            f"exceptions grew past {MAX_QUOTE_EXCEPTIONS}: {len(listed['quote_misses'])}"
        )
    if len(listed["printed_unplaced"]) > MAX_PRINTED_UNPLACED:
        problems.append(
            f"printed_unplaced grew past {MAX_PRINTED_UNPLACED}: {len(listed['printed_unplaced'])}"
        )
    assert not problems, "\n".join(problems)
