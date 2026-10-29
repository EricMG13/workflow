"""Info: the new PACK_TOOL_MODULES branch of `test_tool_use_sections_match_registrations` is not
vacuous. Each mutant of `host._SOURCE_STEPS` must make every CP-0/CP-1/CP-1A row fail; the
unmutated rows pass; a mutant of a module outside those rows leaves them passing."""
from typing import Any

import pytest

from deploy_workflow import host

import test_owner_stage4 as st

ROWS = [(o, m, text) for o, m, text in st.SECTIONS if m in st.PACK_TOOL_MODULES]

MUTANTS: dict[str, dict[str, tuple[str, ...]]] = {
    "cp1-drop-financials": {"CP-1": ("source_context",)},
    "cp1-add-narrative": {"CP-1": ("source_context", "financials", "narrative")},
    "cp0-empty": {"CP-0": ()},
    "cp1a-extra": {"CP-1A": ("business_context", "extra")},
    "cp0-renamed": {"CP-0": ("readiness",)},
}


def test_rows_exist() -> None:
    print("ROWS", len(ROWS), sorted({m for _, m, _ in ROWS}))
    assert {m for _, m, _ in ROWS} == set(st.PACK_TOOL_MODULES)


@pytest.mark.parametrize("row", ROWS, ids=[f"{o}:{m}" for o, m, _ in ROWS])
def test_unmutated_rows_pass(row: Any) -> None:
    st.test_tool_use_sections_match_registrations(*row)


@pytest.mark.parametrize("name", list(MUTANTS))
def test_mutant_fails_its_rows(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    mutant = MUTANTS[name]
    monkeypatch.setattr(host, "_SOURCE_STEPS", {**host._SOURCE_STEPS, **mutant})
    rows = [r for r in ROWS if r[1] in mutant]
    assert rows, name
    survived = []
    for row in rows:
        try:
            st.test_tool_use_sections_match_registrations(*row)
            survived.append(row[:2])
        except AssertionError:
            pass
    print("MUTANT", name, "rows", len(rows), "survived", survived)
    assert not survived


def test_unrelated_mutant_leaves_rows_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(host, "_SOURCE_STEPS", {**host._SOURCE_STEPS, "CP-8": ()})
    for row in ROWS:
        st.test_tool_use_sections_match_registrations(*row)
