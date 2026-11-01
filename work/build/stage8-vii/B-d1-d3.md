# B: D1 + D2 + D3 in the statement extractor (stage contract; mx-feature)

Rules: `W/work/build/stage8-vii/common.md` (read first). Branch: `claude/s8-vii-b`. Edit only
`src/deploy_vii/statement_extract.py` (code and its module docstring, which is the rules' doc)
and new `tests/test_statement_extract_d1_d3.py` and `tests/czr_extract_golden.json`. Do not touch `src/deploy_vii/live/tools.py`,
any precheck, or `tests/test_czr_fixes.py` / `tests/test_source_tools.py`.

## Inputs
| What | Where | Why |
|---|---|---|
| Findings D1, D2, D3 | `K/CONSOLIDATED.md` section 2 | defect and fix direction |
| Probes | `K/probes/v-parse/probe_d1_d3flag.py`, `probe_d2_d3.py` | exact reproducing pages (reuse their PAGE texts in the tests) |
| Extractor | `src/deploy_vii/statement_extract.py` (`_cells` :117, `_is_header` :141, `_headers` :165, `_flags` :183, `extract_statement_lines` :192) | code to change |
| Consumers (read-only) | `src/deploy_workflow/financial_workflow.py` :362-420 (item 70 precheck: `_column_periods(table.headers, …)`, `len(columns) != len(extracted.values)`, `extracted.label in c.quote`); `src/deploy_vii/live/tools.py` `extracted_body` :462 (renders flags generically) | contract the fix must keep |

The contract below was agreed with the Modules session (its H02 task reads `headers`). Rules are exact; do not widen them.

## D2 (Medium): year-valued data rows
Today `_cells` returns None when every numeric cell is a bare year without `$` (:135), so such a row is dropped, and `_headers` may take it into `headers`.
- New rule: a line whose numeric cells are all bare four-digit years (1900-2099, no `$`) is a header line only when its label is empty, or is wholly parenthesised (starts with `(` and ends with `)`), or every word of its label (`_WORD`, case-insensitive) is a month name or one of the period words `year years ended ending fiscal month months week weeks quarter quarters period periods three six nine twelve for the as of at and` or the unit/scale words `in millions thousands billions dollars usd except per share data par value amounts unaudited` (a `$` in the label is allowed). Otherwise it is a data line, read like any other (`"Net revenues  2025  1998"` → label `Net revenues`, values 2025, 1998). Modules amendment: the real CZR year rows are labelled with unit captions, e.g. `(In millions, except per share data) | 2026 | 2025 | 2026 | 2025`, `(Dollars in millions, except par value) | 2025 | 2024`; they must stay headers.
- So `headers` never holds a line the extractor returns as a data line. Keep `_headers`' selection otherwise unchanged. Keep `"Year ended December 31  2025  2024"` a header (existing `tests/test_source_tools.py:121`).
- Update the docstring bullet that says such lines are omitted (review risk 3).

## D3 (Low): footnote marker read as -1
- New rule: when the table's header lines hold N > 0 four-digit years (the existing `years` count, computed after D2) and a data line has exactly N + 1 raw values whose first is `(n)` with one or two digits and no folded `$`, that first cell is a footnote marker: drop it from `raw_values` and `values`, leave `label` unchanged (so `extracted.label in quote` still holds), and add a new flag `footnote_marker` (new `LineFlag` value and constant, after the existing two in the fixed order). Such a line then does not get `more_values_than_header_years`.
- Every other case is unchanged (no years in headers → the marker still reads as -1 and is flagged as today; `(123)` is a value).
- Update the docstring's flag section.

## D1 (Medium): omitted candidate lines
- `ExtractedTable` gains `omitted: tuple[OmittedLine, ...] = ()`, with a new frozen dataclass `OmittedLine(line_no: int, text: str)` (`line_no` 1-based like `ExtractedLine`; `text` the page line as printed, `\r` removed).
- A line is an omitted candidate when it is non-blank, holds two or more whitespace-separated tokens (after the pipe rewrite `_cells` does), its last token fullmatches `_NUMERIC_CELL`, and it is none of: a returned data line; a line of the returned `headers`; a header-shaped line (`_is_header`) whose last token is a bare four-digit year (a second table's period row such as `"June 30, 2026 | December 31, 2025"`). A lone token (a page number) is never a candidate. A single-value row naming a month (`"Balance at December 31, 2024   1,234"`) is a candidate. In page order.
- Examples (probe d1): `"Goodwill                           120"`, `"Inventories                        n/m             300"`, `"Total assets 9,100 8,900"` are omitted; the header line and the data lines are not.
- Update the module docstring ("A line the rules cannot parse is omitted, never stubbed" → recorded in `omitted`).

## Tests (RED first, exact values)
In `tests/test_statement_extract_d1_d3.py`, using the probes' pages:
- D2: probe d2 page → labels include `Net revenues` (raw `("2025", "1998")`) and `Weighted average shares` (`("2010", "1985")`); `headers == ("(In millions)            Years Ended December 31,", "                              2025        2024")` exactly as printed (check against the page text); a `"Year ended December 31  2025  2024"` line above data stays a header.
- D3: same page → `Cost of revenues` has `raw_values == ("900", "800")`, `values == (Decimal("900"), Decimal("800"))`, label `"Cost of revenues"`, flags `("footnote_marker",)`; a page with no year headers keeps `(1)` as -1.
- D1: probe d1 page → `omitted` equals the exact `OmittedLine` tuple for the three lines above; a statement page with only data/header/caption lines has `omitted == ()`; a lone page-number line is not omitted.
- **Must not change (Modules):** the seven filed CZR statement pages keep the same `headers` and the same lines, field for field. The controller generated their output at base 5a1d2e2f into `W/work/build/stage8-vii/czr-extract-golden.json` (list of `{source_id, locator, headers, lines: [{line_no, label, raw_values, values (str or null), indent, caption, flags}]}`). Copy it unchanged to `tests/czr_extract_golden.json` in the RED commit; a parametrised test reads each page as `tests/test_czr_fixes.py:_filed_table` does (`czr_runs.make_pack`, then `extract_statement_lines(text, locator, source_id)`) and asserts `headers` and every line field equal the golden. This test passes at RED and must pass at fix. `omitted` is not compared.
- Name the node ids that fail at RED and why.
- D1 is data only: no precheck or renderer consumes `omitted` in this task (Modules adds that later).
