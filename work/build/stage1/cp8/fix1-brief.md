# CP-8 fix round 1 (after the first adversary review)

Review: `work/build/stage1/cp8/review-adversary.md` (lane worktree). Reviewer probes: `<S>/cp8-adversary/` where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Step 0
`EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a")`, then `git merge claude/module-dev-status-review-0981b6` (lane tip). Report conflicts; resolve none in files outside your two.

## Fix
1. **M1 (Medium).** `readiness.citation_issues` accepts a quote through `deploy_vii.quotes` normalisation (soft hyphen U+00AD deleted; curly quotes, dashes and U+2212 minus mapped; whitespace runs collapsed; hyphen line wraps joined). cp8 then reads figures, dates and labels from the raw quote, so `bid 9­8.00` with `value_text 8.00` validates and T7.3 shows 0.08.
   - Write the failing test first (`p01_soft_hyphen_figure.py` is the case).
   - Fix: every check that reads a value, date, label or text from a quote (`_token_once`, `_labelled`, the `as_of_text` and `text in quote` checks, and any other raw-quote read you find in cp8.py) runs on `quotes.normalise(quote)`. The existing issue wording then fires; add no new wording.
   - Cover a mapped character too (U+2212 minus or an en dash inside a quoted figure or date), not only U+00AD.
2. **L1 (test strength).** Add tests that kill these survivors (runners `p07_mutate.py`, `p07b_mutate.py`):
   - "first figure" relaxed (reachable: `p09_first_figure_reachable.py`);
   - the CP-6-present T7.8 `current_decision` row (assert T7.8 in `test_decision_line_reads_the_cp6_call` or a new test);
   - "value occurs once" relaxed, and the equal-day boundary of the realized after-decision check (use `edited_pack`);
   - the EXACT context dropped (derive and compose), the `N.NN` format (8-15), the equal-day boundary of the default statement, blank `flag_quote`, `isnumeric` replaced by `isdigit`.
   - Justify in one line each, no test: r38 (oracle-reserved), the two `source_authority` guards (Stage 2), citation de-duplication (oracle compares cites by page).
3. **Untested direction.** Add a test for the `_unpinned` raise with the realized side split and the expected side missing.

Not in this round (with LEAD): the split-plus-missing wording; review items "to LEAD" 1–5.

## Rules
- Files: `src/deploy_workflow/owners/cp8.py`, `tests/test_method_cp8.py`. Test-first, red seen for the reported cause.
- No stub, fake value or catch-all. Never edit `cases/` or `src/deploy_vii`.
- Gates (exit 0): `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp8.py`; `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both files. Nothing else.
- Run mutants only from a full temporary copy of the worktree (pyproject `pythonpath` shadows PYTHONPATH-only runs).
- New strings: none expected. If any, run `prose.issues` and `bare_figures` over them and report hits.

## Report
Commit; finding → test; exit codes of `p01_soft_hyphen_figure.py`, `p07_mutate.py`, `p07b_mutate.py`, `p09_first_figure_reachable.py` and your `mutate_r5` runner; gates; `Not verified:`; ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
