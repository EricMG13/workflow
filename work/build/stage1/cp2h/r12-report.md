CP-2H round 12 report (B8 and B10). Worktree agent-a52b5ec0919986ddb, branch worktree-agent-a52b5ec0919986ddb. Step 0: `git merge --ff-only claude/round12` fast-forwarded f843772 to 128c3ca, and HEAD matched 128c3ca.

**Commit:** add5fa8, on top of 128c3ca. It changes only `src/deploy_workflow/owners/cp2h.py` and `tests/test_method_cp2h.py`.

**Rulings and their tests** (from `# Round 12`; the ruling wins over the brief)
- **B8: nothing row-shaped after a block end.**
  - Code: `_block` (cp2h.py:234) now sets `breached=True` when it ends at a line that is not the block's width and any later line on that page has two or more fields. `_rows` raises the block's pinned text at its rows step, so item 8 order holds.
  - The new test `test_row_after_a_block_end_breaches` has 15 cases, `B8_BREACHES`. Each checks `parse_ratings` and that `validate` returns exactly the one issue.
  - Cases, all expecting `Trigger terms not found` unless noted:
    - every "lane today" case: blank line, whitespace-only line, single-tab row, single-space row, and a second header after a blank line;
    - a one-field note followed by a row;
    - a row several lines after the end;
    - a two-field line after the end.
  - Each block's own text: `scale_blank_line` gives `Rating scale not found` and `register_blank_line` gives `Rating register not found`.
  - A header followed at once by an end line, then rows, is breached, not empty. Terms, register and scale versions are each paired with a second edit, so the expected text only arises at the rows step and not at the header step.
  - Item 8 order: a scale B8 breach comes before a register one, and a register one before a terms one.
  - Controls:
    - `test_header_then_end_line_alone_reads_as_no_header`: a header, an end line and nothing row-shaped stays `empty`, refused at the header step.
    - `test_malformed_last_row_is_the_known_limit`: a malformed last row (tab or single space) is pinned as accepted with 4 triggers, with a comment citing the ruling's "Known limit".
  - **Two existing round 11 tests changed, because the ruling contradicts them:**
    - `test_term_block_ends_at_the_first_short_line` expected `End of terms.\nZeta  Watch  X  Over  1x` to compose with 5 triggers. That edit is now the refused case `terms_note_then_row`. The test now checks that one-field notes after the end still compose.
    - `test_one_field_line_ends_a_block` expected the scale blank line to give `Rating not on the scale: Brook Credit Ba3`. That edit is now `scale_blank_line` (`Rating scale not found`). The test keeps the gap page:1 assertion.
  - No frozen case moved.
- **B9:** as built, not touched.
- **B10: Unicode `Cf` characters count as blank.**
  - Test first: I added `BLANK_FIELDS`, covering all 10 analyst text fields: `views[0/1].rationale/limitation`, `overall.rationale/limitation` and `gaps[0].gap/why_it_matters/affected_analysis/action`.
  - A coverage test checks this list against every `str` / `str | None` model field. `agency` is left out as a register key.
  - `test_blank_text_is_refused` runs `BLANK_CASES` through `blank_failure` with the frame `EMPTY_TEXT` = `<path>: empty text`, which is CP-2H's pinned frame. `test_blank_text_twin_is_accepted` checks that text with a trailing ZWSP is not blank.
  - It went red on the 40 Cf cases (blank-5 to blank-8 across the 10 fields); the whitespace cases were already green.
  - Fix: `_prose` (cp2h.py:1479) and `_limitation` (:1492) now use `is_blank`. Null and `""` handling are unchanged. These are the only two blank checks in cp2h.py.
- **B7:** left alone; it is already a plain test.
- **Red at base 128c3ca** (my tests run against HEAD's cp2h.py): 55 failed, the 40 B10 cases and 15 B8 cases. Saved in `<S>/cp2h-r12/red_at_128c3ca.txt`.

**Mutants: `<S>/cp2h-r12/mutants.sh`, exit 0** (log in `mutants.log`). It runs on a full temporary copy with PYTHONDONTWRITEBYTECODE=1. All 7 mutants were killed (pytest exit 1), and the unmutated copy exits 0.
- B10's `Cf` test reverted to `not text.strip()`: at both sites, at the `_prose` site alone, and at the `_limitation` site alone.
- B8 `or after` dropped (the pre-B8 code).
- B8 checking only the next line. This survived the first run, so I added `terms_row_lines_after_the_end`.
- B8 threshold raised to more than 2 fields. This also survived the first run, so I added `terms_two_fields_after_the_end`.
- B8 applied only when the block already has rows.
- W mutants do not apply to CP-2H.

**Probes**
- **LEAD's `p_cp2h_b8_b10.py`, copy at `<S>/cp2h-r12/p_cp2h_b8_b10.py` with LANE pointed at my worktree: exit 1, as expected.**
  - It fails only on the 10 checks that assert the lane bypass still exists: the 5 B8 mid-block cases and the 5 B10 values. All 10 are now refused.
  - Its frozen checks hold: no frozen ratings page is breached, and 0 frozen submission strings change or hold a `Cf` character.
  - The known limit reads 4 triggers.
- **Inverted copy `<S>/cp2h-r12/p_cp2h_b8_b10_after.py`: exit 0.** It has the same cases and requires the module to equal the rule on each.
- **`b2_ruled_residual.py`: exit 0**, all 4 ruled variants refused with `Trigger terms not found`. Run in place it fails on import, because the test module now imports `defect_classes`. So I ran it from a copy at `<S>/cp2h-r12/` whose `_probe_base.py` adds `ROOT/tests` to sys.path; nothing else changed.

**Gates (all exit 0)**
- `pytest tests/test_method_cp2h.py tests/test_defect_classes_selfcheck.py`: 512 passed.
- `ruff check` and `ruff format --check` on the two files. The first run of each failed: once on a literal ZWSP the editor wrote into the twin test (replaced with `​`), and once on formatting of one dict entry.
- `MYPYPATH=src mypy --strict` on the two files.

`<S>` = /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad

Not verified:
- I ran only `test_method_cp2h.py` and the selfcheck, not the full suite.
- GitNexus impact and detect_changes were not run.
- The `methods/cp2h.md` known-limit note and the manifest `parse_rule` text are for the controller and the release batch, and I did not write them.
- The B8 edits I added beyond the ruling's list are not frozen or pinned anywhere; they follow from the rule. These are the header-then-end-line combinations, the scale and register cases, and the two cases added for mutants.
- The two flipped round 11 tests rest on my reading that B8 supersedes them.
- LEAD's probe was not changed beyond its LANE path; its exit 1 is its own bypass expectation.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n` (pytest and mypy passed the first time; the first ruff check and ruff format runs failed as described, and the first mutant run had 2 survivors).
