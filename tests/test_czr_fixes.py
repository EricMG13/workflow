"""CZR gap fixes: the CP-1 statement-heading rule and ` | `-delimited statement rows.

Real headings and rows are read from the filed CZR documents (bytes); the synthetic headings
are the ones the CP-1 precheck matched before this change and must map to the same kinds.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow import financial_workflow as fw

DOCS = Path(__file__).parents[1] / "cases/czr-2026q2-earnings-update/documents"
Q10 = (DOCS / "CZR_Q2_2026_10Q.txt").read_text(encoding="utf-8").split("\n")
K10 = (DOCS / "CZR_FY2025_10K.txt").read_text(encoding="utf-8").split("\n")


def _kinds(text: str) -> list[str]:
    return [m.group().strip() for m in fw.STATEMENT_HEADING.finditer(text)]


@pytest.mark.parametrize(
    "heading",
    [
        "CONSOLIDATED CONDENSED BALANCE SHEETS",
        "CONSOLIDATED CONDENSED STATEMENTS OF OPERATIONS",
        "CONSOLIDATED CONDENSED STATEMENTS OF CASH FLOWS",
        "CONSOLIDATED BALANCE SHEETS",
        "CONSOLIDATED STATEMENTS OF OPERATIONS",
        "CONSOLIDATED STATEMENTS OF CASH FLOWS",
    ],
)
def test_real_headings_are_located(heading: str) -> None:
    assert heading in "\n".join(Q10 + K10)
    assert _kinds(f"x\n{heading}\n(UNAUDITED)") == [heading]


@pytest.mark.parametrize(
    "heading",
    [
        "INCOME STATEMENT",
        "CASH FLOW STATEMENT",
        "BALANCE SHEET",
        "CONSOLIDATED INCOME STATEMENT",
        "CONSOLIDATED CASH FLOW STATEMENT",
        "CONSOLIDATED BALANCE SHEET",
        "  CONSOLIDATED BALANCE SHEET  ",
    ],
)
def test_synthetic_headings_still_located(heading: str) -> None:
    assert _kinds(f"a\n{heading}\nb") == [heading.strip()]


@pytest.mark.parametrize(
    "line",
    [
        "NOTES TO CONSOLIDATED CONDENSED FINANCIAL STATEMENTS",
        "CONSOLIDATED CONDENSED STATEMENTS OF COMPREHENSIVE INCOME (LOSS)",
        "CONSOLIDATED CONDENSED STATEMENTS OF STOCKHOLDERS’ EQUITY",
        "Consolidated Balance Sheets as of December 31, 2025 and 2024",
        "BALANCE SHEET DATA",
    ],
)
def test_other_lines_are_not_headings(line: str) -> None:
    assert _kinds(f"a\n{line}\nb") == []


def test_real_pages_have_a_located_heading_per_statement() -> None:
    assert sum(1 for line in Q10 if fw.STATEMENT_HEADING.fullmatch(line)) == 3
    assert sum(1 for line in K10 if fw.STATEMENT_HEADING.fullmatch(line)) == 3


def test_earnings_workflow_uses_the_same_rule() -> None:
    from deploy_workflow import earnings_workflow as ew

    assert ew.STATEMENT_HEADING is fw.STATEMENT_HEADING


# --- Gap 2 -------------------------------------------------------------------------------------


def test_pipe_rows_of_the_real_10q_extract() -> None:
    text = "\n".join(Q10[103:112])  # statements of operations, header and first rows
    table = extract_statement_lines(text, "page:1")
    by_label = {line.label: line for line in table.lines}
    casino = by_label["Casino"]
    assert casino.raw_values == ("1,759", "1,668", "3,425", "3,262")
    assert casino.values == (Decimal(1759), Decimal(1668), Decimal(3425), Decimal(3262))
    assert by_label["Net revenues"].raw_values == ("2,993", "2,907", "5,863", "5,701")
    assert all(line.label and "|" not in line.label for line in table.lines)
    assert any("Six Months Ended" in header for header in table.headers)


def test_pipe_negative_nil_and_dollar_cells() -> None:
    text = "\n".join(
        [
            "(In millions) | 2026 | 2025",
            "Other, net | (12) | —",
            "Cash | $965 | $887",
        ]
    )
    lines = extract_statement_lines(text, "page:1").lines
    assert [(x.label, x.raw_values, x.values) for x in lines] == [
        ("Other, net", ("(12)", "—"), (Decimal(-12), None)),
        ("Cash", ("965", "887"), (Decimal(965), Decimal(887))),
    ]


def test_pipe_separator_rows_give_no_line() -> None:
    text = "(In millions) | 2026 | 2025\n|---|---|---|\n--- | --- | ---\nCash | 1 | 2"
    assert [x.label for x in extract_statement_lines(text, "page:1").lines] == ["Cash"]


def test_pipe_prose_row_gives_no_line() -> None:
    text = "Item 1. | Business | 4\nSee Note | 2"
    assert extract_statement_lines(text, "page:1").lines == ()


def test_space_rows_extract_as_before() -> None:
    text = "Year ended December 31  2025  2024\nNet profit  16  13\nWorking capital  (2)  2"
    lines = extract_statement_lines(text, "page:1").lines
    assert [(x.label, x.raw_values) for x in lines] == [
        ("Net profit", ("16", "13")),
        ("Working capital", ("(2)", "2")),
    ]
