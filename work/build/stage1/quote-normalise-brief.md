# Raw-quote reads after a normalised quote match (CP-1D, CP-3D)

The CP-8 adversary review (`work/build/stage1/cp8/review-adversary.md`, M1) found this defect class. `readiness.citation_issues` (src/deploy_vii/readiness.py:116) accepts a quote through `deploy_vii.quotes`. That normalisation deletes U+00AD, maps curly quotes, the dashes in `_DASHES` (including U+2212 minus) to `-`, collapses whitespace runs, and joins hyphen line wraps. An owner that then reads a figure, date, label or name from the **raw** quote can store a value the page does not state. In CP-8, `bid 9­8.00` with `value_text 8.00` validated, and T7.3 showed 0.08.

Your module may have the same class. Confirm or rule it out test-first.

## Step 0
- `EnterWorktree(path="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/<worktree>")`
- `git merge --ff-only claude/module-dev-status-review-0981b6`

## Process
1. List every place in your owner file that reads from a quote's raw text after it was located: regex findall, `in quote`, label or token checks, date parsing.
   - CP-1D starts at `_basis_amounts` (cp1d.py:503).
   - CP-3D starts at `_labelled`, `as_of_text in o.quote`, `_check_quoted_numeral`, `name in quote` and `date_text in term.quote.quote` (cp3d.py:437-640). Also check whether `out.on_page` uses `citation_issues`/`quotes.quoted` or a check of its own.
2. For each read, write a test with a quote that the locator check accepts but that holds U+00AD, or a mapped dash or minus, inside the figure, date or label.
   - The test asserts that the validator refuses, using the existing issue wording, or that the composed value equals what the page states.
   - Watch it fail.
3. **If red:** fix by running that read on `quotes.normalise(quote)`, so it reads the same text the match used. Add no new wording.
4. **If not red:** keep the test as a guard and report the read as not reproduced, with the reason.

## Rules
- Allowed files: `src/deploy_workflow/owners/<cp>.py` and `tests/test_method_<cp>.py` only.
- Never edit `cases/` or `src/deploy_vii`.
- No stub, fake value or catch-all.
- Gates, all exit 0:
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_<cp>.py`
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
  - Run nothing else.
- Run mutants only from a full temporary copy of the worktree. Show that each fix's test kills the revert.

## Report
- the commit;
- a table of reads, each with its test and verdict (fixed or not reproduced);
- the mutant exit code;
- gate results;
- a `Not verified:` line;
- the ledger line `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`.
