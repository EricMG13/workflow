# B report (D1 + D2 + D3) — written by the controller from the builder's text report and its own runs

- Builder: mx-feature; worktree `.claude/worktrees/agent-a7fa497acc06ce436`, branch `claude/s8-vii-b`, base 5a1d2e2f. RED 24f0a5af (tests + `tests/czr_extract_golden.json`, cmp-identical to the controller's golden), fix 0a4917ed (`src/deploy_vii/statement_extract.py` only).
- D2: `_cells` keeps an all-bare-year line as data unless `_is_period_label` (empty, wholly parenthesised, or every word a month/period/unit word). `_headers` → `_header_indexes` (same selection, returns indexes).
- D3: `_Cells.first_dollar`; first cell `(n)` (1-2 digits, no `$`) with N+1 values and N>0 header years is dropped from raw_values/values; flag `footnote_marker` (last in order); no `more_values_than_header_years` then.
- D1: frozen `OmittedLine(line_no, text)`; `ExtractedTable.omitted` default `()`; candidate rule as briefed. Builder notes: a `- | - | -` separator row now counts as an omitted candidate under the literal rule.
- Golden test `test_filed_czr_pages_read_as_they_did_before` (7 filed CZR pages: headers + every line field).

## Controller runs (lane venv, builder worktree)
- RED @24f0a5af: `tests/test_statement_extract_d1_d3.py` → collection error `ImportError: cannot import name 'OmittedLine'` (the whole file is red at RED; the golden was generated at base, so it holds there by construction).
- Fix @0a4917ed: `tests/test_statement_extract_d1_d3.py` 21 passed. Running: `tests/test_source_tools.py tests/test_czr_fixes.py tests/test_czr_driver.py tests/test_czr_case.py` (slow; result to follow in the ledger).
- ruff check: predating TRY004 ×5 (same as base). **New: SIM905 ×3** statement_extract.py:83-85 (`"...".split()` word sets), **FLY002 ×4** tests/test_statement_extract_d1_d3.py:18, :32, :107, :131.
- ruff format --check: 0.
- mypy strict on statement_extract.py: base 0; **fix 4 errors** :305 (`ExtractedLine` assigned to a `str` variable), :309 ×3 (`replace`/`append`/`_flags` on that variable) — a loop variable name reused for `str` and `ExtractedLine`.
