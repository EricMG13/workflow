# B fix round 2 (mx-feature, resumed builder) — from the whole-branch review

Same rules and files as `B-d1-d3.md`. **Base: the integration branch.** In your worktree run `git checkout -b claude/s8-vii-b2 2f7c56adc61fa763ee0e89763093d3d216c3aefd` (it holds B, B fix 1, and the other groups). Commits: `test: RED D2 D3 fix 2` (tests only) then `fix: D2 D3 fix 2` (code and docstring only).

Whole-branch review (mx-precise) probes: `W/work/build/stage8-vii/probes/final-review/p4_footnote_change_column.py`, `p5_notes_header.py` (each exits 1 while its defect is present).

## Findings (rulings by the controller)
- **M1 Medium (D3, `statement_extract.py` ~:257-263).** In a table with a printed change column (`2025  2024  Change`), a real first value `(12)` is taken as a footnote marker and dropped, shifting the row's values (probe p4).
  Ruling: D3 also requires the marker to sit left of the year columns: the marker cell's end column (in the line as `_cells` reads it, after the pipe rewrite) must be less than the start column of the leftmost four-digit year (`_YEAR`) in the header lines (read the same way, after the pipe rewrite). Otherwise the line is read as today (the cell is a value and `more_values_than_header_years` applies). Carry the column you need out of `_cells` in the existing `_Cells` record (like `first_dollar`). Update the docstring's D3 sentence.
  Expected on the probes' pages: probe p4 → no line flagged `footnote_marker`, `Other income (expense), net` keeps `("(12)", "(8)", "(4)")` with `more_values_than_header_years`; probe d2/d1 pages (existing D3 tests) unchanged (the marker `(1)` ends before the first header year).
- **M2 Medium (D2 word list, ~:82-89).** An IFRS-style header row `Notes  2025  2024` reads as a data line, so `headers` is empty and a note number then passes as an unflagged first value (probe p5).
  Ruling: add `note` and `notes` to the header word list (with the period/unit words). Update the docstring's D2 sentence.

## Tests (RED first, exact values)
In `tests/test_statement_extract_d1_d3.py`: the probe p4 page (exact raw_values and flags for all three lines, `headers` exact); the probe p5 page (`headers == ("Notes  2025  2024" line as printed,)` or the exact header block, and the `Revenue` line keeps `more_values_than_header_years`). Every existing test stays green, including the golden test.

Report as before (SHAs, RED node ids, `Not verified:`).
