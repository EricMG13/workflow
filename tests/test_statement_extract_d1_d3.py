"""D1-D3 of the statement extractor (stage 8-vii): omitted candidate lines, year-valued data
rows and footnote markers. The filed CZR pages must read exactly as they did before."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from czr_runs import make_pack

from deploy_vii.statement_extract import OmittedLine, extract_statement_lines

GOLDEN = json.loads((Path(__file__).parent / "czr_extract_golden.json").read_text("utf-8"))

D2_HEAD = "(In millions)            Years Ended December 31,"
D2_YEARS = "                              2025        2024"
D2_PAGE = "\n".join(
    [
        "CONSOLIDATED STATEMENTS OF OPERATIONS",
        D2_HEAD,
        D2_YEARS,
        "Net revenues                  2025        1998",
        "Cost of revenues  (1)          900         800",
        "Operating income               1125        1198",
        "Weighted average shares        2010        1985",
        "Net income                      700         650",
    ]
)

D1_HEAD = "                         December 31, 2025    December 31, 2024"
D1_PAGE = "\n".join(
    [
        "CONSOLIDATED BALANCE SHEETS",
        D1_HEAD,
        "Cash and equivalents  (1)          500             400",
        "Goodwill                           120",
        "Inventories                        n/m             300",
        "Total assets 9,100 8,900",
        "Total liabilities                  4,000           3,900",
    ]
)


def test_d2_year_valued_rows_are_data_and_headers_stay_clean() -> None:
    table = extract_statement_lines(D2_PAGE, "page:1")
    assert table.headers == (D2_HEAD, D2_YEARS)
    by_label = {line.label: line for line in table.lines}
    assert by_label["Net revenues"].raw_values == ("2025", "1998")
    assert by_label["Net revenues"].values == (Decimal(2025), Decimal(1998))
    assert by_label["Weighted average shares"].raw_values == ("2010", "1985")
    assert [line.label for line in table.lines] == [
        "Net revenues",
        "Cost of revenues",
        "Operating income",
        "Weighted average shares",
        "Net income",
    ]


@pytest.mark.parametrize(
    "caption",
    [
        "(In millions, except per share data)",
        "(Dollars in millions, except par value)",
        "Year ended December 31",
        "Three Months Ended June 30,",
        "$ in thousands",
        "",
    ],
)
def test_d2_period_and_unit_labels_stay_headers(caption: str) -> None:
    year_row = f"{caption}  2026  2025"
    page = f"ASSETS\n{year_row}\nCash and equivalents   10   20"
    table = extract_statement_lines(page, "page:1")
    assert table.headers == (year_row,)
    assert [line.label for line in table.lines] == ["Cash and equivalents"]


def test_d2_other_label_makes_a_year_row_data() -> None:
    table = extract_statement_lines("Net revenues  2025  1998", "page:1")
    assert [(line.label, line.raw_values) for line in table.lines] == [
        ("Net revenues", ("2025", "1998"))
    ]
    assert table.headers == ()


def test_d3_footnote_marker_is_dropped_and_flagged() -> None:
    table = extract_statement_lines(D2_PAGE, "page:1")
    cost = next(line for line in table.lines if line.label == "Cost of revenues")
    assert cost.raw_values == ("900", "800")
    assert cost.values == (Decimal(900), Decimal(800))
    assert cost.flags == ("footnote_marker",)
    others = [line for line in table.lines if line is not cost]
    assert all(line.flags == () for line in others)


def test_d3_without_header_years_the_marker_still_reads_as_minus_one() -> None:
    page = "Cost of revenues  (1)  900  800"
    (line,) = extract_statement_lines(page, "page:1").lines
    assert line.raw_values == ("(1)", "900", "800")
    assert line.values == (Decimal(-1), Decimal(900), Decimal(800))
    assert line.flags == ()


def test_d3_three_digit_parenthesis_and_dollar_first_cell_are_values() -> None:
    page = "\n".join(
        [
            "Year ended December 31  2025  2024",
            "Alpha  (123)  900  800",
            "Beta  $ (1)  900  800",
        ]
    )
    alpha, beta = extract_statement_lines(page, "page:1").lines
    assert alpha.raw_values == ("(123)", "900", "800")
    assert alpha.flags == ("more_values_than_header_years",)
    assert beta.raw_values == ("(1)", "900", "800")
    assert beta.flags == ("more_values_than_header_years",)


def test_d1_unparsed_candidate_lines_are_omitted_in_page_order() -> None:
    table = extract_statement_lines(D1_PAGE, "page:1")
    assert table.omitted == (
        OmittedLine(line_no=4, text="Goodwill                           120"),
        OmittedLine(line_no=5, text="Inventories                        n/m             300"),
        OmittedLine(line_no=6, text="Total assets 9,100 8,900"),
    )


def test_d1_clean_page_and_lone_page_number_omit_nothing() -> None:
    clean = "\n".join(
        [
            "ASSETS",
            "June 30, 2026 | December 31, 2025",
            "Cash | 1 | 2",
            "NOTES",
            "June 30, 2026 | December 31, 2025",
            "12",
        ]
    )
    assert extract_statement_lines(clean, "page:1").omitted == ()
    assert extract_statement_lines(D2_PAGE, "page:1").omitted == ()


def test_d1_single_value_month_row_is_a_candidate() -> None:
    page = "Cash  1  2\nBalance at December 31, 2024   1,234\r"
    table = extract_statement_lines(page, "page:1")
    assert table.omitted == (OmittedLine(line_no=2, text="Balance at December 31, 2024   1,234"),)


def _golden_id(entry: dict[str, Any]) -> str:
    return f"{entry['source_id']}-{entry['locator']}"


@pytest.mark.parametrize("entry", GOLDEN, ids=_golden_id)
def test_filed_czr_pages_read_as_they_did_before(entry: dict[str, Any]) -> None:
    pack = make_pack()
    source = next(s for s in pack.sources if s.source_id == entry["source_id"])
    text = next(s.text for s in source.spans if s.locator == entry["locator"])
    table = extract_statement_lines(text, entry["locator"], entry["source_id"])
    assert list(table.headers) == entry["headers"]
    got = [
        {
            "line_no": line.line_no,
            "label": line.label,
            "raw_values": list(line.raw_values),
            "values": [None if v is None else str(v) for v in line.values],
            "indent": line.indent,
            "caption": line.caption,
            "flags": list(line.flags),
        }
        for line in table.lines
    ]
    assert got == entry["lines"]


@pytest.mark.parametrize("separator", ["- | - | -", "| - | - |", "  —  |  —  "])
def test_d1_separator_row_of_nil_dashes_and_pipes_is_not_a_candidate(separator: str) -> None:
    page = f"ASSETS\nCash  1  2\n{separator}\nDebt  3  4"
    assert extract_statement_lines(page, "page:1").omitted == ()


def test_d1_labelled_single_nil_row_stays_a_candidate() -> None:
    row = "Goodwill                           —"
    table = extract_statement_lines(f"Cash  1  2\n{row}", "page:1")
    assert table.omitted == (OmittedLine(line_no=2, text=row),)
