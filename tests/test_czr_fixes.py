"""CZR gap fixes: the CP-1 statement-heading rule and ` | `-delimited statement rows.

Real headings and rows are read from the filed CZR documents (bytes); the synthetic headings
are the ones the CP-1 precheck matched before this change and must map to the same kinds.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from czr_runs import make_pack

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
    text = "\n".join(Q10[103:116])  # statements of operations, header and first rows
    table = extract_statement_lines(text, "page:1")
    by_label = {line.label: line for line in reversed(table.lines)}  # first of a label wins
    casino = by_label["Casino"]
    assert casino.raw_values == ("1,759", "1,668", "3,425", "3,262")
    assert casino.values == (Decimal(1759), Decimal(1668), Decimal(3425), Decimal(3262))
    assert by_label["Net revenues"].raw_values == ("2,993", "2,907", "5,863", "5,701")
    assert all(line.label and "|" not in line.label for line in table.lines)
    assert any("Six Months Ended" in header for header in table.headers)


def test_pipe_negative_nil_and_dollar_cells() -> None:
    text = "(In millions) | 2026 | 2025\nOther, net | (12) | —\nCash | $965 | $887"
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


# --- CP-1 precheck on the filed statement pages ------------------------------------------------


def _period(
    period_id: str,
    kind: str,
    end: date,
    quarter: int | None = None,
    months: int | None = None,
) -> SimpleNamespace:
    """A period ending `end`; its span is `months` calendar months (default: the type's span)."""
    span = months or {"QUARTER": 3, "YTD": end.month, "FY": 12, "LTM": 12}.get(kind, 1)
    index = end.year * 12 + end.month - span
    return SimpleNamespace(
        period_id=period_id,
        period_type=kind,
        fiscal_year=str(end.year),
        fiscal_quarter=quarter,
        start_date=date(index // 12, index % 12 + 1, 1),
        end_date=end,
    )


FILED_PERIODS = (
    _period("q2_26", "QUARTER", date(2026, 6, 30), 2),
    _period("q2_25", "QUARTER", date(2025, 6, 30), 2),
    _period("ytd26", "YTD", date(2026, 6, 30)),
    _period("ytd25", "YTD", date(2025, 6, 30)),
    _period("fy25", "FY", date(2025, 12, 31)),
    _period("fy24", "FY", date(2024, 12, 31)),
    _period("fy23", "FY", date(2023, 12, 31)),
    _period("pe25", "PERIOD_END", date(2025, 12, 31)),
    _period("pe24", "PERIOD_END", date(2024, 12, 31)),
    _period("ltm", "LTM", date(2026, 6, 30)),
)


def _sets(*groups: str) -> tuple[frozenset[str], ...]:
    return tuple(frozenset(g.split()) for g in groups)


# (source id, locator, expected statement, expected column period sets)
FILED_PAGES = [
    ("czr-q2-2026-10q", "page:2", "BS", _sets("q2_26 ytd26", "fy25 pe25")),
    ("czr-q2-2026-10q", "page:4", "IS", _sets("q2_26", "q2_25", "ytd26", "ytd25")),
    ("czr-q2-2026-10q", "page:9", "CFS", _sets("ytd26", "ytd25")),
    ("czr-fy2025-10k", "page:54", "BS", _sets("fy25 pe25", "fy24 pe24")),
    ("czr-fy2025-10k", "page:56", "IS", _sets("fy25", "fy24", "fy23")),
    ("czr-fy2025-10k", "page:60", "CFS", _sets("fy25", "fy24", "fy23")),
    ("czr-q2-2026-release", "page:6", "IS", _sets("q2_26", "q2_25", "ytd26", "ytd25")),
]


def _filed_table(source_id: str, locator: str) -> tuple[str, Any]:
    pack = make_pack()
    source = next(s for s in pack.sources if s.source_id == source_id)
    text = next(s.text for s in source.spans if s.locator == locator)
    return text, extract_statement_lines(text, locator, source_id)


@pytest.mark.parametrize(("source_id", "locator", "statement", "expected"), FILED_PAGES)
def test_filed_page_headers_map_to_period_sets(source_id, locator, statement, expected) -> None:
    _, table = _filed_table(source_id, locator)
    assert fw._column_periods(table.headers, FILED_PERIODS) == expected


@pytest.mark.parametrize(("source_id", "locator", "statement", "expected"), FILED_PAGES)
def test_filed_page_lines_belong_to_the_page_statement(
    source_id, locator, statement, expected
) -> None:
    text, table = _filed_table(source_id, locator)
    assert table.lines
    assert {fw._statement(line.caption, text) for line in table.lines} == {statement}


def test_page_heading_wins_over_caption_and_unknown_page_gives_none() -> None:
    assert fw._statement("CASH FLOW ITEMS", "INCOME STATEMENT") == "IS"
    assert fw._statement("Income", "BALANCE SHEET") == "BS"
    assert fw._statement(None, "x\nINCOME STATEMENT\ny") == "IS"
    assert fw._statement("ASSETS", "no heading here") is None
    both = "CONSOLIDATED BALANCE SHEETS\nCONSOLIDATED STATEMENTS OF OPERATIONS"
    assert fw._statement("ASSETS", both) is None


def test_reconciliation_caption_on_a_cash_flow_page_is_cfs() -> None:
    page = "CONSOLIDATED STATEMENTS OF CASH FLOWS\nSix Months Ended June 30,"
    caption = "ADJUSTMENTS TO RECONCILE NET INCOME TO NET CASH PROVIDED BY OPERATING ACTIVITIES:"
    assert fw._statement(caption, page) == "CFS"


def test_caption_decides_only_when_it_names_a_statement_outright() -> None:
    none = "no heading here"
    both = "CONSOLIDATED BALANCE SHEETS\nCONSOLIDATED STATEMENTS OF OPERATIONS"
    assert fw._statement("CASH FLOW ITEMS", none) == "CFS"
    assert fw._statement("CONSOLIDATED BALANCE SHEET", both) == "BS"
    assert fw._statement("STATEMENTS OF OPERATIONS", none) == "IS"
    assert fw._statement("STATEMENT OF INCOME", both) == "IS"
    assert fw._statement("INCOME STATEMENT", none) == "IS"
    assert fw._statement("STATEMENTS OF EARNINGS", none) == "IS"
    assert fw._statement("STATEMENT OF EARNINGS", both) == "IS"
    assert fw._statement("STATEMENTS OF FINANCIAL POSITION", none) == "BS"
    assert fw._statement("COMPREHENSIVE INCOME", none) is None
    assert fw._statement("Income", none) is None
    assert fw._statement("Income", both) is None


def test_six_month_header_is_not_satisfied_by_a_nine_month_period() -> None:
    six = _period("six", "YTD", date(2026, 6, 30))
    nine = _period("nine", "YTD", date(2026, 6, 30), months=9)
    headers = ("Six Months Ended June 30,", "(In millions) | 2026")
    assert fw._column_periods(headers, (six,)) == _sets("six")
    assert fw._column_periods(headers, (nine,)) is None
    assert fw._column_periods(headers, (six, nine)) == _sets("six")
    nine_headers = ("Nine Months Ended June 30,", "(In millions) | 2026")
    assert fw._column_periods(nine_headers, (six, nine)) == _sets("nine")
    assert fw._column_periods(nine_headers, (six,)) is None


def _spanning(period_id: str, kind: str, start: date, end: date, quarter: int | None = None):
    period = _period(period_id, kind, end, quarter)
    period.start_date = start
    return period


def test_flow_column_matches_by_inclusive_day_count_window() -> None:
    headers = ("Six Months Ended June 30,", "(In millions) | 2026")
    inside = _spanning("in", "YTD", date(2026, 1, 2), date(2026, 6, 30))  # 180 days
    assert fw._column_periods(headers, (inside,)) == _sets("in")
    outside = _spanning("out", "YTD", date(2026, 3, 1), date(2026, 6, 30))  # 122 days
    assert fw._column_periods(headers, (outside,)) is None


def test_period_without_a_start_or_end_date_never_matches_a_flow_column() -> None:
    headers = ("Six Months Ended June 30,", "(In millions) | 2026")
    no_start = _spanning("none", "YTD", None, date(2026, 6, 30))
    assert fw._column_periods(headers, (no_start,)) is None
    no_end = _spanning("none", "YTD", date(2026, 1, 1), date(2026, 6, 30))
    no_end.end_date = None
    assert fw._column_periods(headers, (no_end,)) is None


def test_thirteen_week_quarter_and_fifty_two_week_year_map() -> None:
    quarter = _spanning("q1", "QUARTER", date(2025, 9, 29), date(2025, 12, 28), 1)  # 91 days
    headers = ("Three Months Ended December 28,", "(In millions) | 2025")
    assert fw._column_periods(headers, (quarter,)) == _sets("q1")
    year = _spanning("fy", "FY", date(2024, 9, 30), date(2025, 9, 28))  # 364 days
    headers = ("Years Ended September 28,", "(In millions) | 2025")
    assert fw._column_periods(headers, (year,)) == _sets("fy")
    six = ("Six Months Ended September 28,", "(In millions) | 2025")
    assert fw._column_periods(six, (year,)) is None


def test_annual_header_with_full_date_cells_does_not_fall_back_to_balances() -> None:
    headers = (
        "Years Ended December 31,",
        "(In millions) | December 31, 2025 | December 31, 2024",
    )
    q4 = (
        _period("q425", "QUARTER", date(2025, 12, 31), 4),
        _period("q424", "QUARTER", date(2024, 12, 31), 4),
    )
    assert fw._column_periods(headers, q4) is None


def test_annual_header_with_full_date_cells_maps_fy_periods_only() -> None:
    headers = (
        "Years Ended December 31,",
        "(In millions) | December 31, 2025 | December 31, 2024",
    )
    fy25 = _period("fy25", "FY", date(2025, 12, 31))
    fy24 = _period("fy24", "FY", date(2024, 12, 31))
    q425 = _period("q425", "QUARTER", date(2025, 12, 31), 4)
    q424 = _period("q424", "QUARTER", date(2024, 12, 31), 4)
    assert fw._column_periods(headers, (fy25, fy24, q425, q424)) == _sets("fy25", "fy24")
    assert fw._column_periods(headers, (q425, q424)) is None
    wrong_day = ("Years Ended December 31,", "(In millions) | December 30, 2025")
    assert fw._column_periods(wrong_day, (fy25,)) is None


def test_balance_date_is_wider_than_a_three_months_column() -> None:
    periods = FILED_PERIODS[:1] + FILED_PERIODS[2:3]  # q2_26 and ytd26, both 2026-06-30
    assert fw._column_periods(("(In millions) | June 30, 2026",), periods) == _sets("q2_26 ytd26")
    headers = ("Three Months Ended June 30,", "(In millions) | 2026")
    assert fw._column_periods(headers, periods) == _sets("q2_26")
    headers = ("June 30,", "(In millions) | 2026")
    assert fw._column_periods(headers, periods) == _sets("q2_26 ytd26")


def test_year_count_not_a_multiple_of_span_count_maps_nothing() -> None:
    headers = (
        "Three Months Ended June 30, | Six Months Ended June 30,",
        "(In millions) | 2026 | 2025 | 2026",
    )
    assert fw._column_periods(headers, FILED_PERIODS) is None
    assert fw._column_periods(("Years Ended December 31,", "(In millions)"), FILED_PERIODS) is None


def test_years_without_a_span_row_or_with_overlap_map_nothing() -> None:
    assert fw._column_periods(("(In millions) | 2026 | 2025",), FILED_PERIODS) is None
    two_q = (FILED_PERIODS[0], _period("dup", "QUARTER", date(2026, 6, 30), 2))
    headers = ("Three Months Ended June 30,", "(In millions) | 2026")
    assert fw._column_periods(headers, two_q) is None
    same = ("Years Ended December 31,", "(In millions) | 2025 | 2025")
    assert fw._column_periods(same, FILED_PERIODS) is None


def test_ltm_period_never_matches() -> None:
    ltm = (FILED_PERIODS[-1],)
    assert fw._column_periods(("(In millions) | June 30, 2026",), ltm) is None
    headers = ("Six Months Ended June 30,", "(In millions) | 2026")
    assert fw._column_periods(headers, ltm) is None
