# MODULES.csv: Low batch (stage contract; mx-scaffold, docs only, exact edits)

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s5-modules-csv-lows 7c1a702` (`claude/s5-modules-csv`) and confirm the tip. Edit only `docs/MODULES.csv`.

The file is a CSV with no quoted fields. Edit it with a short Python script that does exact string replacements on the file text. Assert that each old string occurs exactly the number of times stated, and add no commas. Every replacement is limited to the row named; the module id is the first field of the line.

## Edits
1. **Row CP-4C**, cells `tool_execution` and `validated_output` (2 occurrences in that row):
   - old: `the never-wedges test test_a3_model_text_is_refused_or_verbatim_and_never_wedges (s1) had not finished at 09:59`
   - new: `the never-wedges test test_a3_model_text_is_refused_or_verbatim_and_never_wedges alone (s1 10:06 on the final code: 1 passed in 4h46m)`
2. **Row CP-4C**, `next_evidence`: delete `Finish s1 (the never-wedges test); ` (1 occurrence).
3. **Row CP-2H**, `rendering`:
   - (a) old `(51/51 at 23:30; scope delivery rerun on 5cf7f0c 08:13 d1 / 08:33 d0))` → new `(51/51 at 23:30; scope delivery rerun on 5cf7f0c 08:13 d1 / 08:33 d0); G2 cp2h x3 on the final code with round 4 (l1 08:15: 14 passed))`
   - (b) old `native DOM proof of the delivered page` → new `native DOM proof of the delivered page (page predates round 4)`
4. **Row CP-OS**:
   - `rendering`: append `; shell_skip_link fixed in 0d (41a8fdb app.js; skip-link focus passes on all 19 pages)` right after the cell's final `items 61-63)`.
   - `next_evidence`: delete `No ledger line records a separate source fix for the shell_skip_link exception (the skip-link focus check passes in the DOM proof); ` (1 occurrence).
5. **Rendering cells.** In every row named below, replace the old clause `page not regenerated on the navigator fix 3c90773 (same shell CSS; items 61-62)` (1 occurrence per row) with the new text given for that row:
   - **CP-2G:** `pointer hit test failed on both pages before the navigator fix (20 and 12 covered rows); fix in the shared shell CSS 3c90773 (items 61-62); pages not regenerated`
   - **CP-8:** `pointer hit test: refused page 0 covered rows and positive page not hit-tested; fix in the shared shell CSS 3c90773 (items 61-62); pages not regenerated`
   - **CP-1C, CP-1D, CP-2A, CP-2E, CP-2H, CP-3, CP-3C, CP-4, CP-4C, CP-DR:** `pointer hit test not run on this page (the navigator defect of items 61-62 covered rows on module pages with long outlines); fix in the shared shell CSS 3c90773; page not regenerated`

## Checks (report each output and exit code)
- `python3 -I /Users/ericguei/Documents/Deploy\ Workflow/.claude/worktrees/module-dev-status-review-0981b6/work/build/keep/modules-csv/probe_rows.py`, run from your worktree root. If it needs arguments, read its header.
- A check with `csv` that:
  - finds 27 rows of 11 columns;
  - finds no cell containing `had not finished`, `No ledger line records` or `Finish s1`;
  - finds no `page not regenerated on the navigator fix 3c90773 (same shell CSS` left;
  - shows `git diff 7c1a702 -- docs/MODULES.csv` touching only rows CP-1C, CP-1D, CP-2A, CP-2E, CP-2G, CP-2H, CP-3, CP-3C, CP-4, CP-4C, CP-8, CP-DR and CP-OS.

One commit, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Output (return as text, under 400 tokens)
- worktree path and tip SHA;
- the check outputs and exit codes;
- a `Not verified:` line.

Never use bare `git stash`.
